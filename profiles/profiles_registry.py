from profiles.scheduler_profile import SCHEDULER_PROFILE

def determine_subsystem_profile(query: str):
    if "sched" in query.lower():
        return SCHEDULER_PROFILE
    elif "vfs" in query.lower():
        return VFS_PROFILE
    return None