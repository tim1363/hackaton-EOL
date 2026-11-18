"""T2 target filtering and exact-model self-collision checks, independent of ROS."""

import csv
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

LOWER = np.tile([-0.863, -0.686, -2.818], 4)
UPPER = np.tile([0.863, 4.501, -0.888], 4)
HOME = np.tile([0.0, 0.9, -1.8], 4)
MAX_STEP = math.radians(5.0)
JUDGE_SAMPLE_STEP = math.radians(0.1)
# Numerical buffer against the judge's strictly greater than 1 mm penetration.
PENETRATION_LIMIT = -0.0009
MODEL_DIR = Path(__file__).resolve().parent / "model"


class CollisionChecker:
    """Use the published collision geometry and pair list, without visual meshes."""

    def __init__(self, model_dir=MODEL_DIR):
        model_dir = Path(model_dir)
        root = ET.fromstring((model_dir / "go1.xml").read_text())
        # Visual meshes have contype=conaffinity=0 and do not affect the 655
        # tested pairs. Replace each with a tiny non-colliding geom rather than
        # removing it, preserving the official geom IDs in the pair CSV.
        for geom in root.iter("geom"):
            if geom.get("class") == "visual":
                geom.attrib.clear()
                geom.attrib.update({"class": "visual", "type": "sphere", "size": "0.0001"})
        asset = root.find("asset")
        for mesh in list(asset.findall("mesh")):
            asset.remove(mesh)
        scene = (model_dir / "scene.xml").read_text()
        self.model = mujoco.MjModel.from_xml_string(
            scene, assets={"go1.xml": ET.tostring(root, encoding="utf-8")}
        )
        self.data = mujoco.MjData(self.model)
        self.data.qpos[:7] = [0, 0, 1, 1, 0, 0, 0]
        with (model_dir / "t2_collision_pairs.csv").open(newline="") as source:
            rows = csv.DictReader(source)
            self.pairs = frozenset(
                (int(r["geom1_id"]), int(r["geom2_id"]))
                for r in rows if r["diagnostic_policy"] == "checked"
            )
        if self.model.ngeom != 56 or len(self.pairs) != 655:
            raise ValueError("Unexpected Go1 collision model or pair list")

    def safe(self, q):
        self.data.qpos[7:] = q
        # This is the same narrow-phase engine as the official model; the floor
        # is ignored by the published pair list. Contacts are computed at q.
        mujoco.mj_forward(self.model, self.data)
        for contact in self.data.contact[:self.data.ncon]:
            pair = tuple(sorted((int(contact.geom1), int(contact.geom2))))
            if pair in self.pairs and contact.dist < PENETRATION_LIMIT:
                return False
        return True

    def safe_transition(self, start, end):
        distance = float(np.max(np.abs(end - start)))
        # A multiple of the judge's grid includes every judge sample exactly,
        # while also checking the midpoint of each judge interval.
        n = 2 * max(1, math.ceil(distance / JUDGE_SAMPLE_STEP))
        for i in range(n + 1):
            if not self.safe(start + (end - start) * (i / n)):
                return False
        return True


class TargetFilter:
    def __init__(self, checker, initial=HOME):
        self.checker = checker
        self.target = np.asarray(initial, dtype=np.float64).copy()
        if (self.target.shape != (12,) or not np.all(np.isfinite(self.target))
                or np.any(self.target < LOWER) or np.any(self.target > UPPER)
                or not checker.safe(self.target)):
            raise ValueError("Initial target must be finite, in range, and collision-free")

    def apply(self, requested):
        requested = np.asarray(requested, dtype=np.float64)
        if requested.shape != (12,) or not np.all(np.isfinite(requested)):
            return self.target.copy(), False
        bounded = np.clip(requested, LOWER, UPPER)
        candidate = self.target + np.clip(bounded - self.target, -MAX_STEP, MAX_STEP)
        if self.checker.safe_transition(self.target, candidate):
            self.target = candidate
            return self.target.copy(), True
        return self.target.copy(), False
