from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from semantic_runtime.provider_patterns import (
    ProviderPattern
)

VFS_PROVIDER_PATTERNS = [
    ProviderPattern(
        suffix="_fops",
        provider_kind="file_operations",
        struct_type="file_operations",
        macro_name="DEFINE_FILE_OPERATIONS"
    )
]

VFS_PROFILE = (
    SubsystemSemanticProfile(
        subsystem_name="kernel/fs",

        entrypoints=[
            "vfs_read",
            "vfs_write",
            "do_sys_open",
        ],

        low_signal_calls={
            "might_fault",
            "fsnotify_access",
            "fsnotify_modify",
            "rw_verify_area",
            "file_start_write",
            "file_end_write",
            "WARN_ON",
            "BUG_ON",
        },

        execution_spine_boost={
            "vfs_read": 10.0,
            "new_sync_read": 20.0,
        },

        high_value_transitions={
            ("vfs_read", "vfs_readf"): 20.0,
            ("vfs_write", "vfs_writef"): 20.0,
        },

        synthetic_bridges = {
            "new_sync_read":
                "file_operations:read_iter",
        },

        associated_structs={
            "file",
            "inode",
            "file_operations",
            "kiocb",
            "iov_iter",
            "dentry",
        },

        dispatch_provider_files=[
            "fs/ext4/file.c",
            "fs/read_write.c",
            "fs/open.c",
        ],

        provider_patterns=VFS_PROVIDER_PATTERNS,

        valid_dispatch_operations={
            "read",
            "write",
            "read_iter",
            "write_iter",
            "open",
            "release",
            "mmap",
            "fsync",
            "iterate_shared",
        },
        runtime_depth_limit=12,

        terminal_symbols={
            "generic_file_read_iter",
            "filemap_read"
        }
    )
)