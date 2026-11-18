"""Optional diagnostic wrapper around the unchanged T2 ROS node.

Logs acceptance and modification statistics; does not affect filter outputs.
"""
import numpy as np
import safety_node

original_apply = safety_node.TargetFilter.apply
counts = {"total": 0, "rejected": 0, "modified": 0}


def counted_apply(self, requested):
    result, accepted = original_apply(self, requested)
    counts["total"] += 1
    counts["rejected"] += not accepted
    counts["modified"] += np.max(np.abs(np.asarray(requested) - result)) > 1e-5
    if counts["total"] % 100 == 0:
        print("T2_FILTER_COUNTS", counts, flush=True)
    return result, accepted


safety_node.TargetFilter.apply = counted_apply
safety_node.main()
