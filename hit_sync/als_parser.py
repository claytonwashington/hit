import os
import gzip
import xml.etree.ElementTree as ET
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def decompress_als(als_path):
    """Decompress a gzipped .als file and return its XML content as bytes."""
    try:
        with gzip.open(als_path, "rb") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to decompress {als_path}: {e}")
        return None

def compress_als(xml_content, output_path):
    """Compress XML content (bytes) back into a gzipped .als file."""
    try:
        with gzip.open(output_path, "wb") as f:
            f.write(xml_content)
        return True
    except Exception as e:
        logging.error(f"Failed to compress to {output_path}: {e}")
        return False

def parse_referenced_samples(xml_content):
    """
    Parse the XML content of an Ableton set and extract all referenced file paths.
    Looks for <FileRef> and <Path> tags.
    """
    paths = set()
    try:
        root = ET.fromstring(xml_content)
        # Search for all Path elements inside FileRef blocks
        for file_ref in root.findall(".//FileRef"):
            path_elem = file_ref.find(".//Path")
            if path_elem is not None and "Value" in path_elem.attrib:
                val = path_elem.attrib["Value"]
                if val:
                    paths.add(val)
    except Exception as e:
        logging.error(f"Error parsing XML for sample references: {e}")
    return list(paths)

def make_paths_relative(xml_content, project_dir):
    """
    Scan the Ableton Live Set XML and rewrite any absolute paths referencing files 
    inside the project directory to be project-relative. This ensures Ableton 
    can load the assets on other machines without 'Missing Files' errors.
    """
    try:
        root = ET.fromstring(xml_content)
        modified = False
        project_dir_abs = os.path.abspath(project_dir)

        # Iterate through all Path elements
        for path_elem in root.findall(".//FileRef/Path"):
            if "Value" in path_elem.attrib:
                original_path = path_elem.attrib["Value"]
                # If the path is absolute and points inside our project directory
                if os.path.isabs(original_path) and original_path.startswith(project_dir_abs):
                    # Compute relative path
                    rel_path = os.path.relpath(original_path, project_dir_abs)
                    path_elem.attrib["Value"] = rel_path
                    modified = True
                    logging.info(f"Normalized path to relative: {original_path} -> {rel_path}")

        if modified:
            return ET.tostring(root, encoding="utf-8"), True
    except Exception as e:
        logging.error(f"Error normalizing XML paths: {e}")
    
    return xml_content, False
