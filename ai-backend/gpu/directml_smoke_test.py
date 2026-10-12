"""Run a tiny ONNX graph using the DirectML execution provider."""

import tempfile
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto, helper


def main() -> None:
    if "DmlExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError("ONNX Runtime does not expose DmlExecutionProvider.")

    input_info = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1])
    output_info = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1])
    graph = helper.make_graph(
        [helper.make_node("Add", ["input", "input"], ["output"])],
        "directml_smoke_test",
        [input_info],
        [output_info],
    )
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid("", 17)],
    )
    model.ir_version = 9

    with tempfile.TemporaryDirectory(prefix="ai-server-directml-") as temp_dir:
        model_path = Path(temp_dir) / "smoke-test.onnx"
        onnx.save(model, model_path)

        options = ort.SessionOptions()
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.enable_mem_pattern = False
        session = ort.InferenceSession(
            str(model_path),
            sess_options=options,
            providers=["DmlExecutionProvider"],
        )
        result = session.run(None, {"input": np.array([1.5], dtype=np.float32)})[0]

    if not np.allclose(result, np.array([3.0], dtype=np.float32)):
        raise RuntimeError(f"Unexpected DirectML output: {result!r}")

    print(f"DirectML smoke test passed on provider(s): {session.get_providers()}")


if __name__ == "__main__":
    main()
