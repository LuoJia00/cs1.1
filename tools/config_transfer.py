"""Local-only settings transfer. Archives never belong in the Git repository."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import socket
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "API/.env", "global_config.json", "data/api_providers.json",
    "data/prompt_libraries.json", "data/runninghub_workflows.json",
    "static/runninghub/api_providers.json", "static/runninghub/models_registry.json",
}


def backup(root=ROOT, label="settings"):
    folder = root / ".private-transfer"
    folder.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output = folder / f"{label}-{stamp}.zip"
    manifest = {"format": "infinite-canvas-settings-v1", "files": {}}
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(FILES):
            path = root / name
            if not path.is_file():
                continue
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("配置路径指向项目外部，已停止")
            content = path.read_bytes()
            archive.writestr(name, content)
            manifest["files"][name] = hashlib.sha256(content).hexdigest()
        archive.writestr("manifest.json", json.dumps(manifest))
    return output


def restore(source, root=ROOT):
    # Validate the whole archive before writing any configuration.
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(set(names)) or set(names) - FILES - {"manifest.json"}:
            raise ValueError("备份包含重复条目或不允许的文件")
        if sum(item.file_size for item in entries) > 100 * 1024 * 1024:
            raise ValueError("配置包超过 100 MB，已停止")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "infinite-canvas-settings-v1":
            raise ValueError("不是此工具生成的配置备份")
        if set(manifest["files"]) != set(names) - {"manifest.json"}:
            raise ValueError("备份清单不匹配")
        contents = {}
        for name, checksum in manifest["files"].items():
            target = root / name
            if not target.resolve().is_relative_to(root.resolve()):
                raise ValueError("配置目标指向项目外部，已停止")
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != checksum:
                raise ValueError("备份校验失败")
            contents[name] = content
    recovery = backup(root, "before-import")
    previous = {name: (root / name).read_bytes() if (root / name).exists() else None for name in contents}
    try:
        for name, content in contents.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    except Exception:
        for name, content in previous.items():
            target = root / name
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(content)
        raise
    return recovery, len(contents)


def main():
    parser = argparse.ArgumentParser(description="个人配置迁移；不会打包图片、画布或聊天记录")
    parser.add_argument("action", nargs="?", choices=["export", "import"])
    parser.add_argument("archive", nargs="?")
    args = parser.parse_args()
    try:
        with socket.create_connection(("127.0.0.1", 3000), timeout=0.5):
            raise RuntimeError("请先关闭画布服务（3000 端口），再迁移配置")
    except OSError:
        pass
    action = args.action
    if not action:
        print("1. 导出个人配置\n2. 导入个人配置\n备份包含 API 密钥，未加密。仅通过你自己的 U 盘等方式传输，不要上传 GitHub。")
        answer = input("输入 1 或 2：").strip()
        if answer not in {"1", "2"}:
            raise ValueError("已取消")
        action = "export" if answer == "1" else "import"
    if action == "export":
        print("已导出：", backup())
        print("不含图片、聊天、画布、浏览器设置、外部工具登录和电脑路径。")
    else:
        source = args.archive or input("把配置 zip 拖到此窗口，然后按回车：").strip().strip('"')
        print("将覆盖对应的个人配置；现有配置会先自动备份。")
        if input("继续请输入 YES：").strip() != "YES":
            raise ValueError("已取消")
        recovery, count = restore(Path(source))
        print(f"已导入 {count} 个配置文件。原配置备份：{recovery}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("未完成：", exc)
        raise SystemExit(1)
