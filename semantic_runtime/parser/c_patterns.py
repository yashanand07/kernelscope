import re
from typing import Tuple, Optional

# Matches standard kernel iterators (e.g., list_for_each..., for_each_cpu...)
# Captures: Group 1 -> Macro Name, Group 2 -> Arguments String
ITERATOR_PATTERN = re.compile(r'\b([a-zA-Z0-9_]*for_each[a-zA-Z0-9_]*|skb_queue_walk[a-zA-Z0-9_]*)\s*\(([^)]+)\)')

# Maps specific macro names to the 0-indexed position of the COLLECTION argument.
# If a macro is not here, it defaults to index 1 (cursor, collection, ...)
ITERATOR_TARGET_INDEX = {
    # Safe variants inject a temporary storage variable at index 1
    # e.g., list_for_each_entry_safe(pos, n, head, member) -> head is index 2
    "list_for_each_entry_safe": 2,
    "list_for_each_safe": 2,
    "hlist_for_each_entry_safe": 2,
    "hlist_for_each_safe": 2,

    # Hash iterators often place the hashtable at index 0
    # e.g., hash_for_each(name, bkt, node, obj) -> name is index 0
    "hash_for_each": 0,
    "hash_for_each_safe": 0,
    "hash_for_each_rcu": 0,

    # RB-Trees (From your earlier example)
    # e.g., rbtree_postorder_for_each_entry_safe(pos, n, root, field)
    "rbtree_postorder_for_each_entry_safe": 2,
}

def parse_iterator_args(macro_name: str, args_string: str) -> Tuple[str, str, Optional[str]]:
    """
    Decodes the raw argument string of an iterator macro.
    Returns: (cursor_expression, collection_expression, member_field)
    """
    # Naive split by comma (sufficient for 99% of kernel iterators)
    args = [arg.strip() for arg in args_string.split(',')]

    if not args:
        return ("", "", None)

    # 1. Resolve Cursor (usually index 0, except for some hash/bitmap macros)
    # For simplicity in v1, we assume cursor is always at index 0 for the major families,
    # unless it's a known exception we add to another mapping dictionary later.
    cursor_expr = args[0]

    # 2. Resolve Collection
    coll_idx = ITERATOR_TARGET_INDEX.get(macro_name, 1) # Default to 1
    coll_expr = args[coll_idx] if coll_idx < len(args) else ""

    # 3. Resolve Member Field (if applicable)
    member_expr = None
    # If it's an `_entry` iterator, the struct member name is almost always the last argument
    if "_entry" in macro_name and len(args) >= 3:
        member_expr = args[-1]

    return cursor_expr, coll_expr, member_expr