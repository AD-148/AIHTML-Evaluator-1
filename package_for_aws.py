import tarfile
import os
import shutil

def exclude_patterns(tarinfo):
    name = tarinfo.name
    if "node_modules" in name or "__pycache__" in name or ".git" in name or ".env" in name or "venv" in name or "/dist" in name or "\\dist" in name:
        return None
    return tarinfo

def create_package():
    output_filename = "aws_deploy.tar.gz"
    print(f"Creating {output_filename}...")
    
    with tarfile.open(output_filename, "w:gz") as tar:
        # Add Backend
        print("Adding backend...")
        tar.add("backend", arcname="backend", filter=exclude_patterns)
        
        # Add Frontend source (excluding node_modules)
        print("Adding frontend...")
        tar.add("frontend", arcname="frontend", filter=exclude_patterns)
        
        # Add Root files
        tar.add("docker-compose.yml")
        # tar.add(".env") # Usually better to set ENV on server manually
        
    print(f"Package created: {output_filename}")
    print(f"Size: {os.path.getsize(output_filename) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    create_package()
