import re
import os
import pandas as pd


def get_full_latex_text(latex_file):
  r"""
  Reads a LaTeX file, replaces all \input{somefile} and \include{somefile} commands with the content of 
  the referenced files, includes the content of the .bbl file if present, and returns the full expanded LaTeX text.

  Args:
    latex_file (str): Path to the main LaTeX file.

  Returns:
    str: The LaTeX content with all \input{somefile}, \include{somefile} commands replaced by the 
         corresponding file contents and the .bbl file content included if present.

  Raises:
    FileNotFoundError: If the main LaTeX file does not exist.

  Notes:
    - The function assumes that all input files referenced by \input{} or \include{} are located
      in the same directory as the main LaTeX file or in a subdirectory relative
      to it.
    - If a referenced file is not found, a warning is printed and the original 
      \input{} or \include{} command is left unchanged in the content.
    - If a .bbl file with the same base name as the main LaTeX file exists, its content
      is included at the \bibliography{} command position.
  """
  with open(latex_file, 'r') as file:
    content = file.read()

  # Regex pattern to match \input{} and \include{} commands
  pattern = re.compile(r'\\(input|include)\{([^}]+)\}')

  def replace_match(match):
    r"""
    Replaces a matched \input{somefile} or \include{somefile} with the contents of the specified file.

    Args:
      match (re.Match): A regex match object for \input{somefile} or \include{somefile}.

    Returns:
      str: The contents of the specified file or the original \input{} or \include{} command
           if the file is not found.
    """
    input_filename = match.group(2) + '.tex'
    if not os.path.isabs(input_filename):
      input_filename = os.path.join(os.path.dirname(latex_file), input_filename)
    try:
      with open(input_filename, 'r') as input_file:
        return input_file.read()
    except FileNotFoundError:
      print(f"Warning: file '{input_filename}' not found. Leaving the {match.group(1)} command unchanged.")
      return match.group(0)

  # Replace all \input{} and \include{} commands
  content = pattern.sub(replace_match, content)

  # Check for the presence of a .bbl file and include its content if found
  bbl_file = os.path.splitext(latex_file)[0] + '.bbl'
  if os.path.exists(bbl_file):
    with open(bbl_file, 'r') as file:
      bbl_content = file.read()
    
    # Regex pattern to match \bibliography{} command
    bib_pattern = re.compile(r'\\bibliography\{[^}]+\}')

    parts = bib_pattern.split(content, maxsplit=1)
    if len(parts) == 2:
      before_bib = parts[0]
      after_bib = parts[1]      
      content = before_bib + bib_pattern.search(content).group(0) + '\n' + bbl_content + after_bib

  return content


def extract_section_structure(latex_content):
  """
  Extracts sections, subsections, and subsubsections with their content from LaTeX content.

  Args:
      latex_content (str): The LaTeX content as a string.

  Returns:
      dict: A dictionary containing sections, subsections, and subsubsections along with their content.
  """
  sections = {}

  # Regex patterns for sections, subsections, and subsubsections
  section_pattern = re.compile(r'\\section\*?\{(.+?)\}')
  subsection_pattern = re.compile(r'\\subsection\*?\{(.+?)\}')
  subsubsection_pattern = re.compile(r'\\subsubsection\*?\{(.+?)\}')

  section_matches = list(section_pattern.finditer(latex_content))
  for i, section_match in enumerate(section_matches):
    section_title = section_match.group(1)
    sections[section_title] = {'content': '', 'subsections': {}}

    section_start = section_match.start()
    section_end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(latex_content)
    section_content = latex_content[section_start:section_end]

    # Handle subsections within the section
    subsection_matches = list(subsection_pattern.finditer(section_content))
    last_subsection_end = 0
    for j, subsection_match in enumerate(subsection_matches):
      subsection_title = subsection_match.group(1)
      sections[section_title]['subsections'][subsection_title] = {'content': '', 'subsubsections': []}

      subsection_start = subsection_match.start()
      subsection_end = subsection_matches[j + 1].start() if j + 1 < len(subsection_matches) else len(section_content)
      subsection_content = section_content[subsection_start:subsection_end]
      sections[section_title]['subsections'][subsection_title]['content'] = subsection_content

      # Handle subsubsections within the subsection
      subsubsection_matches = list(subsubsection_pattern.finditer(subsection_content))
      last_subsubsection_end = 0
      for k, subsubsection_match in enumerate(subsubsection_matches):
        subsubsection_title = subsubsection_match.group(1)
        subsubsection_start = subsubsection_match.start()
        subsubsection_end = subsubsection_matches[k + 1].start() if k + 1 < len(subsubsection_matches) else len(subsection_content)
        subsubsection_content = subsection_content[subsubsection_start:subsubsection_end]
        sections[section_title]['subsections'][subsection_title]['subsubsections'].append({
          'title': subsubsection_title,
          'content': subsubsection_content
        })

      # Extract the subsection content before subsubsections start
      if j == 0:
        sections[section_title]['subsections'][subsection_title]['content'] = subsection_content[:subsubsection_matches[0].start()] if subsubsection_matches else subsection_content
      else:
        previous_subsection_content = section_content[last_subsection_end:subsection_match.start()]
        sections[section_title]['content'] += previous_subsection_content

      last_subsection_end = subsection_end

    # Extract the section content before subsections start
    if subsection_matches:
      sections[section_title]['content'] += section_content[:subsection_matches[0].start()]
    else:
      sections[section_title]['content'] = section_content

  return sections


def structure_to_dataframe(sections_dict):
  """
  Converts the extracted sections, subsections, and subsubsections into a pandas DataFrame.

  Args:
      sections_dict (dict): A dictionary containing sections, subsections, and subsubsections along with their content.

  Returns:
      pd.DataFrame: A DataFrame with columns 'section', 'subsection', 'subsubsection', and 'content'.
  """
  data = []

  for section_title, section_data in sections_dict.items():
    section_content = section_data['content']
    if section_content:
      data.append([section_title, '', '', section_content])

    for subsection_title, subsection_data in section_data['subsections'].items():
      subsection_content = subsection_data['content']
      if subsection_content:
        data.append([section_title, subsection_title, '', subsection_content])

      for subsubsection in subsection_data['subsubsections']:
        subsubsection_title = subsubsection['title']
        subsubsection_content = subsubsection['content']
        data.append([section_title, subsection_title, subsubsection_title, subsubsection_content])

  df = pd.DataFrame(data, columns=['section', 'subsection', 'subsubsection', 'content'])
  return df


def extract_bibliography(latex_content):
  """
  Extracts the bibliography section from LaTeX content.

  Args:
      latex_content (str): The LaTeX content as a string.

  Returns:
      str: The bibliography section as a string, if found; otherwise, an empty string.
  """
  bibliography_pattern = re.compile(r'\\thebibliography\{(.+?)\}|\\begin\{thebibliography\}(.+?)\\end\{thebibliography\}', re.DOTALL)
  
  bibliography_match = bibliography_pattern.search(latex_content)
  if bibliography_match:
    return bibliography_match.group(0)
  
  return ""


def remove_bibliography(latex_content):
  """
  Removes the bibliography section from LaTeX content.

  Args:
      latex_content (str): The LaTeX content as a string.

  Returns:
      str: The LaTeX content with the bibliography section removed.
  """
  bibliography_pattern = re.compile(r'\\thebibliography\{(.+?)\}|\\begin\{thebibliography\}(.+?)\\end\{thebibliography\}', re.DOTALL)
  
  return bibliography_pattern.sub('', latex_content)


def split_bibliography(bibliography_content, max_bytes=10000):
    """
    Splits the bibliography into parts that do not exceed the specified number of bytes.

    Args:
        bibliography_content (str): The bibliography content as a string.
        max_bytes (int): The maximum number of bytes for each part.

    Returns:
        list: A list of strings, each representing a part of the bibliography.
    """
    bibitem_pattern = re.compile(r'\\bibitem(?:\[[^\]]+\])?\{[^}]+\}(?:.|\s)*?(?=\\bibitem|\Z)', re.DOTALL)
    bibitems = bibitem_pattern.findall(bibliography_content)
    
    parts = []
    current_part = ""
    current_size = 0

    for bibitem in bibitems:
        bibitem_size = len(bibitem.encode('utf-8'))
        
        if current_size + bibitem_size > max_bytes:
            parts.append(current_part)
            current_part = ""
            current_size = 0

        current_part += bibitem + "\n"
        current_size += bibitem_size

    if current_part:
        parts.append(current_part)
    
    return parts


def extract_abstract(latex_content):
  """
  Extracts the abstract from LaTeX content.

  Args:
    latex_content (str): The LaTeX content as a string.

  Returns:
    str: The abstract if found; otherwise, an empty string.
  """
  abstract_pattern = re.compile(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', re.DOTALL)
  abstract_match = abstract_pattern.search(latex_content)
  if abstract_match:
    return abstract_match.group(1).strip()
  return ""


def extract_abstract(latex_content):
  """
  Extracts the abstract from LaTeX content.

  Args:
    latex_content (str): The LaTeX content as a string.

  Returns:
    str: The abstract if found; otherwise, an empty string.
  """
  abstract_pattern = re.compile(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', re.DOTALL)
  abstract_match = abstract_pattern.search(latex_content)
  if abstract_match:
    return '\\begin{abstract}' + abstract_match.group(1) + '\\end{abstract}'
  return ""

def find_matching_brace(text, start_pos):
  """
  Finds the position of the matching closing brace for the opening brace at start_pos.

  Args:
    text (str): The text containing braces.
    start_pos (int): The position of the opening brace.

  Returns:
    int: The position of the matching closing brace.
  """
  open_braces = 1
  for pos in range(start_pos + 1, len(text)):
    if text[pos] == '{':
      open_braces += 1
    elif text[pos] == '}':
      open_braces -= 1
    if open_braces == 0:
      return pos
  return -1

def extract_title(latex_content):
    """
    Extracts the title from LaTeX content.

    Args:
        latex_content (str): The LaTeX content as a string.

    Returns:
        str: The title if found; otherwise, an empty string.
    """
    title_pattern = re.compile(r'\\title\{')
    title_match = title_pattern.search(latex_content)
    if title_match:
        start_pos = title_match.end() - 1
        end_pos = find_matching_brace(latex_content, start_pos)
        if end_pos != -1:
            return latex_content[start_pos + 1:end_pos]
    return ""


def extract_authors(latex_content):
  """
  Extracts the author information from LaTeX content.

  Args:
    latex_content (str): The LaTeX content as a string.

  Returns:
    str: The author information if found; otherwise, an empty string.
  """
  author_pattern = re.compile(r'\\author\{')
  author_match = author_pattern.search(latex_content)
  if author_match:
    start_pos = author_match.end() - 1
    end_pos = find_matching_brace(latex_content, start_pos)
    if end_pos != -1:
      return '\\author{' + latex_content[start_pos + 1:end_pos] + '}'
  return ""


def extract_newcommands(latex_content):
  """
  Extracts \newcommand definitions from LaTeX content.

  Args:
    latex_content (str): The LaTeX content as a string.

  Returns:
    str: A string containing all \newcommand definitions found in the content.
  """
  newcommand_pattern = re.compile(r'^\\newcommand.*$', re.MULTILINE)
  matches = newcommand_pattern.findall(latex_content)
  
  return '\n'.join(matches)

def structure_to_toc(sections_dict):
    """
    Converts the extracted sections, subsections, and subsubsections into a Markdown unordered list.

    Args:
        sections_dict (dict): A dictionary containing sections, subsections, and subsubsections along with their content.

    Returns:
        str: A string representing the table of contents as a Markdown unordered list.
    """
    toc_lines = []

    for section_title, section_data in sections_dict.items():
        toc_lines.append(f"- {section_title}")
        for subsection_title, subsection_data in section_data['subsections'].items():
            toc_lines.append(f"  - {subsection_title}")
            for subsubsection in subsection_data['subsubsections']:
                toc_lines.append(f"    - {subsubsection['title']}")

    return "\n".join(toc_lines)


def process(latex_file, instruction_template=None):
  """
  Processes a LaTeX file to extract its title, abstract, authors, sections, subsections, subsubsections,
  and bibliography, and returns this information as a pandas DataFrame. Optionally formats and returns
  an instruction string using a provided template.

  Args:
    latex_file (str): Path to the main LaTeX file.
    instruction_template (str, optional): A template string for instructions. If provided, the title and table of contents
                                          (ToC) will be formatted into this template.

  Returns:
    pd.DataFrame: A DataFrame containing the extracted information.
    str: An instruction string formatted with the title and ToC if `instruction_template` is provided.
  """

  latex_content = get_full_latex_text(latex_file)

  bib = extract_bibliography(latex_content)
  bib_parts = split_bibliography(bib, 10000)
  latex_content = remove_bibliography(latex_content) 
  
  structure = {
    'Abstract': {
      'content': extract_abstract(latex_content),
      'subsections': {},
    },
    'Authors': {
      'content': extract_authors(latex_content),
      'subsections': {},
    },
  }
  structure.update(extract_section_structure(latex_content))
  structure.update({
    f'Bibliography_{i+1}' if len(bib_parts) > 1 else 'Bibliography': {
      'content': b,
      'subsections': {},
    } for i, b in enumerate(bib_parts)
  })

  df = structure_to_dataframe(structure)
  toc = structure_to_toc(structure)

  if instruction_template is None:
    return df

  title = extract_title(latex_content)
  inst = instruction_template.format(title=title, toc=toc)
  
  if new_cmds := extract_newcommands(latex_content):
    inst += f"""

**New LaTeX commands**:

```latex
{new_cmds}
```
"""

  return df, inst


if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser(description='Process a LaTeX file to extract information for RAG.')
  parser.add_argument('latex_file', type=str, help='Path to the main LaTeX file')
  parser.add_argument('-o', '--output', type=str, required=True, help='Path to the output CSV file')
  parser.add_argument('-t', '--template', type=str, help='Path to the instruction template text file', default=None)
  parser.add_argument('--inst', type=str, help='Path to the output instruction text file', default=None)
  args = parser.parse_args()

  if args.inst and not args.template:
    parser.error("--inst requires --template to be specified.")

  if args.template:
    with open(args.template, 'r') as f:
      template = f.read()
    df, inst = process(args.latex_file, template)
    if args.inst:
      with open(args.inst, 'w') as f:
        f.write(inst)
    else:
      print(inst)
  else:
    df = process(args.latex_file)
  
  df.to_csv(args.output, index=False)