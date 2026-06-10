# =============================================================================
# 2. NETWORKING (NET) PROFILE
# =============================================================================
from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from semantic_runtime.provider_patterns import (
    ProviderPattern
)
NET_PROVIDER_PATTERNS = [
    ProviderPattern(
        suffix="_netdev_ops",
        provider_kind="net_device_ops",
        struct_type="net_device_ops",
        macro_name=""
    ),
    ProviderPattern(
        suffix="_prot",
        provider_kind="socket_protocol",
        struct_type="proto",
        macro_name=""
    )
]

NET_PROFILE = (
    SubsystemSemanticProfile(
        subsystem_name="net",

        entrypoints=["netif_receive_skb", "dev_queue_xmit", "napi_poll", "tcp_v4_rcv"],

        low_signal_calls={
            "skb_get",
            "kfree_skb",
            "consume_skb",
            "rcu_read_lock",
            "rcu_read_unlock",
            "local_bh_disable",
            "local_bh_enable",
            "skb_reserve",
        },

        execution_spine_boost={
            "netif_receive_skb": 10.0,
            "__netif_receive_skb": 10.0,
            "__netif_receive_skb_core": 10.0,
            "ip_rcv": 10.0,
            "ip_local_deliver": 10.0,
            "tcp_v4_rcv": 10.0,
            "dev_queue_xmit": 10.0,
            "__dev_queue_xmit": 10.0,
            "napi_poll": 10.0,
            "__napi_poll": 10.0,
        },

        high_value_transitions={
            ("netif_receive_skb", "__netif_receive_skb"): 20.0,
            ("__netif_receive_skb", "__netif_receive_skb_core"): 20.0,
            ("dev_queue_xmit", "__dev_queue_xmit"): 20.0,
            ("napi_poll", "__napi_poll"): 20.0,
            ("ip_local_deliver", "tcp_v4_rcv"): 15.0, # IP to TCP layer bridge
        },

        synthetic_bridges={
            "__napi_poll": "napi_struct:poll",
            "__dev_queue_xmit": "net_device_ops:ndo_start_xmit",
            "sk_prot_recvmsg": "proto:recvmsg",
        },

        associated_structs={
            "sk_buff",
            "net_device",
            "napi_struct",
            "sock",
            "rtable",
            "net_device_ops",
            "proto",
        },

        dispatch_provider_files=[
            "net/core/dev.c",
            "net/ipv4/tcp_ipv4.c",
            "net/ipv4/ip_input.c",
            "net/ipv4/ip_output.c"
        ],

        provider_patterns=NET_PROVIDER_PATTERNS,

        valid_dispatch_operations={
            "ndo_start_xmit",
            "poll",
            "recvmsg",
            "sendmsg",
            "handler",
        },

        runtime_depth_limit=20, # Network stacks tend to be deeper
        terminal_symbols=set() #yashtbd
    )
)