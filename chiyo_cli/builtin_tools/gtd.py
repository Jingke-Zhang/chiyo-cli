"""Framework-backed GTD built-in for Org agenda items."""

import json
import subprocess

from chiyo_cli.paths import compact_path
from chiyo_cli.toolkit import PickOpenTool, ToolError, require_command


DEFAULT_CONFIG = {
    "fzf_prompt": "gtd> ",
    "emacsclient": "emacsclient",
    "emacsclient_open_args": ["-n"],
    "agenda_span": "day",
    "agenda_start_day": "",
}


AGENDA_ITEMS_EXPRESSION = r"""
(progn
  (require 'org)
  (require 'org-agenda)
  (require 'json)
  (require 'subr-x)
  (let ((org-agenda-buffer-name " *chiyo-gtd-agenda*")
        (org-agenda-sticky nil)
        (org-agenda-window-setup 'current-window)
        (org-agenda-span __AGENDA_SPAN__)
        (org-agenda-start-day __AGENDA_START_DAY__))
    (save-window-excursion
      (org-agenda-list)
      (with-current-buffer org-agenda-buffer-name
        (let (items)
          (goto-char (point-min))
          (while (not (eobp))
            (let* ((marker (or (get-text-property (point) 'org-marker)
                               (get-text-property (point) 'org-hd-marker)))
                   (line-text (string-trim
                               (buffer-substring-no-properties
                                (line-beginning-position)
                                (line-end-position)))))
              (when (and marker (marker-buffer marker) line-text
                         (not (string-empty-p line-text)))
                (with-current-buffer (marker-buffer marker)
                  (save-excursion
                    (goto-char marker)
                    (let ((file (buffer-file-name))
                          (line (line-number-at-pos))
                          (column (1+ (current-column)))
                          (heading (ignore-errors
                                     (org-get-heading t t t t)))
                          (todo (or (org-get-todo-state) ""))
                          (category (or (org-get-category) "")))
                      (when file
                        (push `((title . ,(or heading line-text))
                                (agenda . ,line-text)
                                (todo . ,todo)
                                (category . ,category)
                                (file . ,file)
                                (line . ,line)
                                (column . ,column))
                              items)))))))
            (forward-line 1))
          (json-encode (vconcat (nreverse items))))))))
"""


def emacs_lisp_string(value):
    if value in (None, ""):
        return "nil"

    return json.dumps(str(value))


def emacs_lisp_agenda_span(value):
    if isinstance(value, int):
        return str(value)

    if str(value).isdigit():
        return str(value)

    return "'" + str(value).replace("'", "")


def agenda_items_expression(config):
    return (
        AGENDA_ITEMS_EXPRESSION
        .replace("__AGENDA_SPAN__", emacs_lisp_agenda_span(config.get("agenda_span", "day")))
        .replace("__AGENDA_START_DAY__", emacs_lisp_string(config.get("agenda_start_day")))
    )


def parse_emacs_json(stdout):
    text = stdout.strip()

    if not text:
        return []

    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        decoded = text

    if isinstance(decoded, str):
        return json.loads(decoded)

    return decoded


def run_emacsclient_eval(command, expression):
    require_command(command)
    result = subprocess.run(
        [command, "-e", expression],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise ToolError(f"{command} failed: {detail}")

    return result.stdout


def emacsclient_open_command(command, item, open_args=None):
    open_args = list(open_args or ["-n"])
    return [
        command,
        *open_args,
        f"+{item['line']}:{item.get('column', 1)}",
        item["file"],
    ]


def emacsclient_open_action(command, item, open_args=None):
    require_command(command)
    return emacsclient_open_command(command, item, open_args)


def agenda_items(config):
    return parse_emacs_json(
        run_emacsclient_eval(
            config["emacsclient"],
            agenda_items_expression(config),
        )
    )


class Tool(PickOpenTool):
    name = "GTD"
    cmd = "gtd"
    author = "Chiyo CLI"
    author_id = "Jingke-Zhang"
    description = "Search Org agenda items and open the source location."
    shell = True
    docs = """
    # gtd

    Search Org agenda items with fzf and open the selected source location
    through emacsclient.
    """
    prompt = "gtd> "
    default_config = DEFAULT_CONFIG
    search_display_fields = [1, 2, 3, 4]

    def add_arguments(self, parser):
        parser.add_argument(
            "--print-elisp",
            action="store_true",
            help="Print the Emacs Lisp expression used to collect agenda items.",
        )

    def items(self, config):
        return agenda_items(config)

    def match(self, item, query, config):
        if not query:
            return True

        haystack = " ".join(
            str(item.get(key, ""))
            for key in ("todo", "title", "agenda", "category", "file")
        ).lower()
        return all(term in haystack for term in query.lower().split())

    def sort_key(self, item, config):
        return (item.get("file", ""), item.get("line", 0))

    def display_fields(self, item, config):
        location = f"{compact_path(item['file'])}:{item['line']}"
        return [
            self.primary(item.get("todo") or "-"),
            self.plain(item.get("title") or item.get("agenda", "")),
            self.secondary(item.get("category", "")),
            self.secondary(location),
        ]

    def completion_items(self, config):
        return []

    def run(self, argv=None, config=None, execute_shell_actions=True):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv)

        if args.print_elisp:
            expression = agenda_items_expression(config)
            print(expression)
            return expression

        return super().run(argv, config, execute_shell_actions)

    def open_item(self, item, args, config):
        try:
            return self.shell_command(
                emacsclient_open_action(
                    config["emacsclient"],
                    item,
                    config.get("emacsclient_open_args", ["-n"]),
                )
            )
        except ToolError as error:
            self.fail(str(error))
