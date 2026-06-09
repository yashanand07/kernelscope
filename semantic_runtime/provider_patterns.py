from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass
class ProviderPattern:

    suffix: str

    provider_kind: str

    struct_type: str

    macro_name: Optional[str] = None

# PROVIDER_PATTERNS = [
#     ProviderPattern(
#         suffix="_sched_class",
#         provider_kind="scheduler_class",
#         struct_type="sched_class",
#         macro_name="DEFINE_SCHED_CLASS",
#     ),

#     ProviderPattern(
#         suffix="_fops",
#         provider_kind="file_operations",
#         struct_type="file_operations",
#         macro_name="DEFINE_FILE_OPS",
#     ),

#     ProviderPattern(
#         suffix="_ops",
#         provider_kind="generic_ops",
#         struct_type="generic_ops",
#         macro_name="DEFINE_GENERIC_OPS",
#     ),
# ]