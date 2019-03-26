import re

# common latex symbols which are not operators
_LATEX_SYMBOLS = {
  '\\leq': ' ≤ ',
  '\\geq': ' ≥ ',
  '\\dots': '... '
}

# common latex operators
_LATEX_OPS = {
  "\\sqrt": '√'
}

def translate(line):
  tags = re.findall("\$\S*?.*?\S*?\$", line)
  for tag in tags:
    stripped_tag = "\033[1;31m" + tag[1:-1] + "\033[0m"
    line = line.replace(tag, stripped_tag)
  for symbol in _LATEX_SYMBOLS:
    line = line.replace(symbol, _LATEX_SYMBOLS[symbol])

  complete = False
  while not complete:
    complete = True
    for op in _LATEX_OPS:
      new_line = re.sub("\\%s\s*?\{(.*)\}" % op, _LATEX_OPS[op] + r"(\1)", line)
      if new_line != line:
        line = new_line
        complete = False
  return line
