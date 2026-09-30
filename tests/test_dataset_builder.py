from pathlib import Path
import tempfile
from PIL import Image
from pk_studio.core.dataset_builder import build_yolo_dataset

def test_build_yolo_dataset_creates_training_layout():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/"src"; out=Path(td)/"out"
        (root/"images").mkdir(parents=True); (root/"labels").mkdir()
        (root/"classes.txt").write_text("cat\ndog\n",encoding="utf-8")
        for i in range(10):
            Image.new("RGB",(32,32)).save(root/"images"/f"im{i}.jpg")
            (root/"labels"/f"im{i}.txt").write_text(f"{i%2} 0.5 0.5 0.5 0.5\n",encoding="utf-8")
        r=build_yolo_dataset(root,out)
        assert sum(r.counts.values())==10
        assert (out/"data.yaml").exists()
        assert (out/"classes.txt").read_text(encoding="utf-8").splitlines()==["cat","dog"]
        assert (out/"train"/"images").is_dir()
