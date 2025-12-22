import tarfile
import os

def make_tarfile(output_filename, source_dirs):
    with tarfile.open(output_filename, "w:gz") as tar:
        for source in source_dirs:
            # Filter function to exclude node_modules and pycache
            def filter_func(tarinfo):
                if "node_modules" in tarinfo.name or "__pycache__" in tarinfo.name or "dist" in tarinfo.name:
                    return None
                return tarinfo
            
            tar.add(source, arcname=os.path.basename(source), filter=filter_func)
            print(f"Added {source}")

make_tarfile("deploy_v3.tar.gz", ["backend", "frontend", "docker-compose.yml", "parallel_batch_processor.py"])
