from semantic_runtime.engine import KernelScopeEngine

def test_kernelscope_regression():
    engine = KernelScopeEngine(workspace_dir="./semantic_context_cache")
    result = engine.compile(driver="linux", chunks_path="chunks.jsonl")

    assert result.success, f"Compilation failed: {result.error}"
    assert result.metrics.peak_rss_mb < 100.0, f"RSS memory spiked to {result.metrics.peak_rss_mb} MB"
    assert result.artifacts.all_exist(), "Database artifacts are missing from cache"

    print("🎉 REGRESSION PASSED SUCCESSFULLY")

if __name__ == "__main__":
    test_kernelscope_regression()