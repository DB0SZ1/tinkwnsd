import os
from utils.logger import get_logger

logger = get_logger(__name__)

def append_memory_log(line: str):
    """
    Appends a new log line to the Post Log section of persona/memory.md.
    Expects line format: [Platform] | [Arc] | [Core point] | [Date]
    """
    persona_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "persona")
    memory_path = os.path.join(persona_dir, "memory.md")
    
    if not os.path.exists(memory_path):
        logger.error("memory.md not found in persona directory.")
        return

    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find the end of the Post Log table
        # Look for the |---| divider or the last table row
        new_lines = []
        in_table = False
        table_end_idx = -1
        
        for i, l in enumerate(lines):
            if "## Post Log" in l:
                in_table = True
            if in_table and "|" in l:
                table_end_idx = i
            elif in_table and l.strip() == "" and table_end_idx != -1:
                # We found a blank line after a table, this is where we insert
                break

        if table_end_idx != -1:
            # Ensure the line starts with a pipe if it doesn't already
            if not line.strip().startswith("|"):
                line = f"| {line.strip()} |"
            
            # Insert after the last table row
            lines.insert(table_end_idx + 1, f"{line}\n")
            
            with open(memory_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            logger.info("Successfully updated memory.md with new post log.")
        else:
            # Fallback: Just append to the end of the file if table not found
            with open(memory_path, "a", encoding="utf-8") as f:
                f.write(f"\n| {line.strip()} |\n")
            logger.warning("Post Log table not found in memory.md, appended to end.")
            
    except Exception as e:
        logger.error(f"Failed to update memory.md: {e}")
