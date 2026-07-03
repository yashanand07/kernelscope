import json
import tempfile
import os

class MockDriver:
    """Provides inline structural text chunks to verify the compiler mechanics."""
    
    @staticmethod
    def get_chunks_and_db():
        # Setup temporary testing file natively
        tmp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".jsonl")
        tmp.write(json.dumps({"file": "kernel/sched/core.c", "content": "LIST_HEAD(clkdm_list);"}) + "\n")
        
        func_src = (
            "void schedule(struct device *dev, int cpu) {\n"
            "    struct clockdomain *temp_clkdm;\n"
            "    int cpu;\n"
            "    list_for_each_entry_safe(temp_clkdm, n, &clkdm_list, node) {\n"
            "        spin_lock(&macro_lock);\n"
            "        clkdm_register(temp_clkdm, &cpu);\n"
            "    }\n"
            "}"
        )
        tmp.write(json.dumps({
            "symbol_id": "func:kernel/sched/core.c:schedule",
            "file": "kernel/sched/core.c",
            "content": func_src
        }) + "\n")
        tmp.close()
        
        mock_symbol_db = {"clkdm_list": [None]}
        return tmp.name, mock_symbol_db, lambda: os.unlink(tmp.name)