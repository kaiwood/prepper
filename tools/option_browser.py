from __future__ import annotations

import curses
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_SRC_DIR = PROJECT_ROOT / "app" / "src"

if str(APP_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(APP_SRC_DIR))

try:
    from prepper_cli.system_prompts import (  # type: ignore
        get_default_system_prompt_name,
        list_prompt_descriptors,
    )
except Exception:  # pragma: no cover - fallback for incomplete setup
    get_default_system_prompt_name = None
    list_prompt_descriptors = None


class OptionBrowserError(RuntimeError):
    pass


@dataclass(frozen=True)
class Choice:
    value: str
    label: str


@dataclass(frozen=True)
class OptionSpec:
    key: str
    label: str
    kind: str
    help_text: str
    choices: tuple[Choice, ...] = ()
    placeholder: str = ""


@dataclass(frozen=True)
class CategorySpec:
    key: str
    label: str
    description: str
    options: tuple[OptionSpec, ...]
    setup_confirmation: bool = False


def _choice(value: str, label: str | None = None) -> Choice:
    return Choice(value=value, label=label or value)


def _prompt_choices() -> tuple[Choice, ...]:
    if list_prompt_descriptors is None:
        prompt_dir = APP_SRC_DIR / "prepper_cli" / "prompts"
        choices = [
            _choice(path.stem)
            for path in sorted(prompt_dir.glob("*.md"))
            if path.is_file()
        ]
    else:
        choices = [
            Choice(value=descriptor.id, label=f"{descriptor.name} ({descriptor.id})")
            for descriptor in list_prompt_descriptors()
        ]

    default_name = None
    if get_default_system_prompt_name is not None:
        try:
            default_name = get_default_system_prompt_name()
        except Exception:
            default_name = None

    if default_name:
        decorated = []
        for choice in choices:
            label = f"{choice.label} [default]" if choice.value == default_name else choice.label
            decorated.append(Choice(choice.value, label))
        choices = decorated

    return tuple(choices)


def build_categories() -> tuple[CategorySpec, ...]:
    prompt_choices = _prompt_choices()
    return (
        CategorySpec(
            key="dev",
            label="Dev",
            description="Run local development services.",
            options=(
                OptionSpec(
                    "target",
                    "Target",
                    "choice",
                    "Choose which development service to run. All starts backend and frontend together.",
                    (_choice("all", "All services"), _choice("backend", "Backend only"), _choice("frontend", "Frontend only")),
                ),
                OptionSpec(
                    "color",
                    "Color output",
                    "toggle",
                    "Force colored runner and child-process output.",
                ),
            ),
        ),
        CategorySpec(
            key="benchmark",
            label="Benchmark",
            description="Run a simulated interview and score interviewer quality.",
            options=(
                OptionSpec(
                    "output",
                    "Output",
                    "choice",
                    "Transcript streams the interview and prints evaluation at the bottom. JSON hides the transcript and prints result JSON.",
                    (_choice("transcript", "Transcript"), _choice("json", "JSON")),
                ),
                OptionSpec("style", "Interview style", "choice", "Prompt/interview style to evaluate.", prompt_choices),
                OptionSpec("candidate", "Candidate", "choice", "Candidate simulation profile.", (_choice("strong", "Strong candidate"), _choice("weak", "Weak candidate"))),
                OptionSpec("difficulty", "Difficulty", "choice", "Optional difficulty override.", (_choice("", "Prompt default"), _choice("easy"), _choice("medium"), _choice("hard"))),
                OptionSpec("language", "Language", "choice", "Language for interview responses.", (_choice("en", "English"), _choice("de", "German"), _choice("fr", "French"))),
                OptionSpec("question_limit", "Question limit", "input", "Optional scored-question roundtrip limit.", placeholder="default"),
                OptionSpec("pass_threshold", "Pass threshold", "input", "Optional pass-score threshold override.", placeholder="default"),
                OptionSpec("model", "Runtime model", "input", "Optional runtime chat and candidate-generation model override.", placeholder="default"),
                OptionSpec("benchmark_model", "Benchmark model", "input", "Optional final scoring model override.", placeholder="default"),
                OptionSpec("temperature", "Temperature", "input", "Optional runtime model temperature override.", placeholder="prompt default"),
                OptionSpec("top_p", "Top-p", "input", "Optional runtime model top-p override.", placeholder="prompt default"),
                OptionSpec("frequency_penalty", "Frequency penalty", "input", "Optional runtime frequency penalty override.", placeholder="prompt default"),
                OptionSpec("presence_penalty", "Presence penalty", "input", "Optional runtime presence penalty override.", placeholder="prompt default"),
                OptionSpec("max_tokens", "Max tokens", "input", "Optional runtime max token override.", placeholder="prompt default"),
                OptionSpec("color", "Color output", "toggle", "Enable colored transcript output. Transcript benchmark mode defaults to color on."),
            ),
        ),
        CategorySpec(
            key="test",
            label="Test",
            description="Run one or more test suites.",
            options=(
                OptionSpec("suite", "Suite", "choice", "Choose which test suite to run.", (_choice("all", "All suites"), _choice("backend", "Backend"), _choice("frontend", "Frontend"), _choice("cli", "CLI"), _choice("tools", "Tools"))),
                OptionSpec("color", "Color output", "toggle", "Force colored runner and child-process output."),
            ),
        ),
        CategorySpec(
            key="interactive",
            label="Interactive",
            description="Start an interactive prepper-cli interview.",
            options=(
                OptionSpec("style", "Interview style", "choice", "Prompt/interview style for this session.", prompt_choices),
                OptionSpec("difficulty", "Difficulty", "choice", "Optional difficulty override.", (_choice("", "Prompt default"), _choice("easy"), _choice("medium"), _choice("hard"))),
                OptionSpec("language", "Language", "choice", "Optional response language override.", (_choice("", "Prompt default"), _choice("en", "English"), _choice("de", "German"), _choice("fr", "French"))),
                OptionSpec("question_limit", "Question limit", "input", "Optional scored-question roundtrip limit.", placeholder="default"),
                OptionSpec("pass_threshold", "Pass threshold", "input", "Optional pass-score threshold override.", placeholder="default"),
                OptionSpec("model", "Runtime model", "input", "Optional runtime chat model override.", placeholder="default"),
                OptionSpec("temperature", "Temperature", "input", "Optional runtime model temperature override.", placeholder="prompt default"),
                OptionSpec("top_p", "Top-p", "input", "Optional runtime model top-p override.", placeholder="prompt default"),
                OptionSpec("frequency_penalty", "Frequency penalty", "input", "Optional runtime frequency penalty override.", placeholder="prompt default"),
                OptionSpec("presence_penalty", "Presence penalty", "input", "Optional runtime presence penalty override.", placeholder="prompt default"),
                OptionSpec("max_tokens", "Max tokens", "input", "Optional runtime max token override.", placeholder="prompt default"),
                OptionSpec("color", "Color output", "toggle", "Enable colored interactive transcript output."),
            ),
        ),
        CategorySpec(
            key="setup",
            label="Setup",
            description="Create env files, Python venvs, and install dependencies.",
            options=(),
            setup_confirmation=True,
        ),
    )


def default_state(category: CategorySpec, *, force_color: bool = False) -> dict[str, str | bool]:
    state: dict[str, str | bool] = {}
    for option in category.options:
        if option.kind == "toggle":
            state[option.key] = force_color or (
                category.key == "benchmark" and option.key == "color"
            )
        elif option.kind == "choice":
            state[option.key] = option.choices[0].value if option.choices else ""
        else:
            state[option.key] = ""
    return state


def build_argv(category_key: str, state: dict[str, str | bool]) -> tuple[str, ...]:
    if category_key == "dev":
        argv = ["--dev"]
        target = str(state.get("target") or "all")
        if target != "all":
            argv.append(f"--{target}")
        elif state.get("target") == "all":
            argv.append("--all")
        if state.get("color"):
            argv.append("--color")
        return tuple(argv)

    if category_key == "test":
        argv = ["--test"]
        suite = str(state.get("suite") or "all")
        argv.append(f"--{suite}")
        if state.get("color"):
            argv.append("--color")
        return tuple(argv)

    if category_key == "setup":
        return ("--setup",)

    if category_key not in {"interactive", "benchmark"}:
        raise ValueError(f"Unknown option browser category: {category_key}")

    output = str(state.get("output") or "transcript")
    argv = ["--benchmark-json"] if category_key == "benchmark" and output == "json" else []
    if category_key == "benchmark" and output != "json":
        argv.append("--benchmark")
    if category_key == "interactive":
        argv.append("--interactive")

    _append_value(argv, "--interview-style", state.get("style"))
    _append_value(argv, "--difficulty", state.get("difficulty"))
    _append_value(argv, "--language", state.get("language"))
    _append_value(argv, "--question-limit", state.get("question_limit"))
    _append_value(argv, "--pass-threshold", state.get("pass_threshold"))
    _append_value(argv, "--model", state.get("model"))
    if category_key == "benchmark":
        candidate = str(state.get("candidate") or "strong")
        if candidate == "weak":
            argv.append("--weak-candidate")
        _append_value(argv, "--benchmark-model", state.get("benchmark_model"))
    _append_value(argv, "--temperature", state.get("temperature"))
    _append_value(argv, "--top-p", state.get("top_p"))
    _append_value(argv, "--frequency-penalty", state.get("frequency_penalty"))
    _append_value(argv, "--presence-penalty", state.get("presence_penalty"))
    _append_value(argv, "--max-tokens", state.get("max_tokens"))
    if state.get("color") and not (category_key == "benchmark" and output == "json"):
        argv.append("--color")
    return tuple(argv)


def _append_value(argv: list[str], flag: str, value: str | bool | None) -> None:
    if isinstance(value, bool) or value is None:
        return
    stripped = value.strip()
    if stripped:
        argv.extend([flag, stripped])


def run(force_color: bool = False) -> tuple[str, ...] | None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise OptionBrowserError(
            "Option browser requires an interactive terminal. Pass an explicit mode such as --dev, --test, --interactive, --benchmark, or --setup."
        )
    return curses.wrapper(lambda stdscr: _Browser(stdscr, force_color).run())


class _Browser:
    def __init__(self, stdscr, force_color: bool) -> None:
        self.stdscr = stdscr
        self.force_color = force_color
        self.categories = build_categories()
        self.states = {
            category.key: default_state(category, force_color=force_color)
            for category in self.categories
        }
        self.category_index = 0
        self.option_index = 0
        self.selected_category: CategorySpec | None = None
        self.message = ""

    def run(self) -> tuple[str, ...] | None:
        curses.curs_set(0)
        curses.use_default_colors()
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_GREEN, -1)

        while True:
            if self.selected_category is None:
                result = self._category_screen()
            else:
                result = self._option_screen(self.selected_category)
            if result is not None:
                return result

    def _category_screen(self) -> tuple[str, ...] | None:
        while self.selected_category is None:
            self._draw_category_screen()
            key = self.stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                self.category_index = max(0, self.category_index - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                self.category_index = min(len(self.categories) - 1, self.category_index + 1)
            elif key in (10, 13, curses.KEY_ENTER):
                self.selected_category = self.categories[self.category_index]
                self.option_index = 0
            elif key == ord("?"):
                self._popup(self.categories[self.category_index].description)
            elif key == 27:
                return ()
        return None

    def _option_screen(self, category: CategorySpec) -> tuple[str, ...] | None:
        options = category.options
        while self.selected_category is category:
            self._draw_option_screen(category)
            key = self.stdscr.getch()
            if key in (curses.KEY_UP, ord("k")) and options:
                self.option_index = max(0, self.option_index - 1)
            elif key in (curses.KEY_DOWN, ord("j")) and options:
                self.option_index = min(len(options), self.option_index + 1)
            elif key == ord("?"):
                if options and self.option_index < len(options):
                    self._popup(options[self.option_index].help_text)
                else:
                    self._popup(category.description)
            elif key == 27:
                self.selected_category = None
                self.message = ""
            elif key == ord(" ") and options and self.option_index < len(options):
                self._activate_option(category, options[self.option_index], prefer_toggle=True)
            elif key in (10, 13, curses.KEY_ENTER):
                if options and self.option_index < len(options):
                    self._activate_option(category, options[self.option_index], prefer_toggle=False)
                    continue
                argv = self._review(category)
                if argv is not None:
                    return argv
        return None

    def _draw_base(self, title: str) -> None:
        self.stdscr.erase()
        self._add(0, 2, "Prepper option browser", curses.color_pair(1) | curses.A_BOLD)
        self._add(1, 2, title, curses.A_BOLD)
        self._add(3, 2, "Use ↑/↓ to move, Enter to select/run, Space to toggle, ? for help, Esc to go back.")

    def _draw_category_screen(self) -> None:
        self._draw_base("Choose a category")
        for offset, category in enumerate(self.categories):
            attr = curses.color_pair(2) if offset == self.category_index else 0
            marker = ">" if offset == self.category_index else " "
            self._add(5 + offset, 4, f"{marker} {category.label:<12} {category.description}", attr)
        self._add_message()
        self.stdscr.refresh()

    def _draw_option_screen(self, category: CategorySpec) -> None:
        self._draw_base(f"{category.label} options")
        state = self.states[category.key]
        if not category.options:
            self._add(5, 4, category.description)
            self._add(7, 4, "Press Enter to review this command.")
        for offset, option in enumerate(category.options):
            attr = curses.color_pair(2) if offset == self.option_index else 0
            marker = ">" if offset == self.option_index else " "
            value = self._display_value(option, state.get(option.key))
            self._add(5 + offset, 4, f"{marker} {option.label:<19} {value}", attr)
        run_row = 6 + len(category.options)
        attr = curses.color_pair(2) if self.option_index == len(category.options) else 0
        marker = ">" if self.option_index == len(category.options) else " "
        self._add(run_row, 4, f"{marker} Review and run", attr)
        self._add_message()
        self.stdscr.refresh()

    def _display_value(self, option: OptionSpec, value: str | bool | None) -> str:
        if option.kind == "toggle":
            return "[■]" if value else "[ ]"
        if option.kind == "choice":
            for choice in option.choices:
                if choice.value == value:
                    return choice.label
            return option.placeholder or "unset"
        text = str(value or "").strip()
        return text if text else f"<{option.placeholder or 'empty'}>"

    def _activate_option(self, category: CategorySpec, option: OptionSpec, *, prefer_toggle: bool = False) -> None:
        state = self.states[category.key]
        if option.kind == "toggle":
            state[option.key] = not bool(state.get(option.key))
        elif option.kind == "choice" and not prefer_toggle:
            state[option.key] = self._choice_screen(option, str(state.get(option.key) or ""))
        elif option.kind == "input" and not prefer_toggle:
            state[option.key] = self._input_value(option, str(state.get(option.key) or ""))

    def _choice_screen(self, option: OptionSpec, current: str) -> str:
        index = next((i for i, choice in enumerate(option.choices) if choice.value == current), 0)
        while True:
            self._draw_base(option.label)
            self._add(4, 2, option.help_text, curses.color_pair(3))
            for offset, choice in enumerate(option.choices):
                attr = curses.color_pair(2) if offset == index else 0
                marker = ">" if offset == index else " "
                selected = " [■]" if choice.value == current else ""
                self._add(6 + offset, 4, f"{marker} {choice.label}{selected}", attr)
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                index = max(0, index - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                index = min(len(option.choices) - 1, index + 1)
            elif key in (10, 13, curses.KEY_ENTER):
                return option.choices[index].value
            elif key == 27:
                return current
            elif key == ord("?"):
                self._popup(option.help_text)

    def _input_value(self, option: OptionSpec, current: str) -> str:
        curses.curs_set(1)
        curses.echo()
        self._draw_base(option.label)
        self._add(4, 2, option.help_text, curses.color_pair(3))
        self._add(6, 2, f"Current: {current or option.placeholder or 'empty'}")
        self._add(8, 2, "New value (blank clears): ")
        self.stdscr.refresh()
        try:
            raw = self.stdscr.getstr(8, 28, 160)
        finally:
            curses.noecho()
            curses.curs_set(0)
        return raw.decode("utf-8").strip()

    def _review(self, category: CategorySpec) -> tuple[str, ...] | None:
        argv = build_argv(category.key, self.states[category.key])
        while True:
            self._draw_base(f"Review {category.label}")
            self._add(5, 4, "Command:")
            self._add(6, 4, "./prepper.sh " + " ".join(argv), curses.color_pair(4) | curses.A_BOLD)
            if category.setup_confirmation:
                self._add(8, 4, "Setup creates env files, Python virtualenvs, and installs dependencies.", curses.color_pair(3))
                self._add(10, 4, "Press y to run setup, or n/Esc to go back.")
            else:
                self._add(8, 4, "Press Enter to run, or Esc to go back.")
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key == 27:
                return None
            if category.setup_confirmation and key in (ord("y"), ord("Y")):
                return argv
            if category.setup_confirmation and key in (ord("n"), ord("N")):
                return None
            if not category.setup_confirmation and key in (10, 13, curses.KEY_ENTER):
                return argv

    def _popup(self, text: str) -> None:
        lines = list(_wrap(text, 68)) or [""]
        height = min(len(lines) + 4, curses.LINES - 2)
        width = min(76, curses.COLS - 4)
        top = max(1, (curses.LINES - height) // 2)
        left = max(2, (curses.COLS - width) // 2)
        win = curses.newwin(height, width, top, left)
        win.box()
        win.addstr(1, 2, "Help", curses.A_BOLD)
        for index, line in enumerate(lines[: height - 4]):
            win.addstr(2 + index, 2, line[: width - 4])
        win.addstr(height - 2, 2, "Press any key to close.")
        win.refresh()
        win.getch()

    def _add_message(self) -> None:
        if self.message:
            self._add(curses.LINES - 2, 2, self.message, curses.color_pair(3))

    def _add(self, y: int, x: int, text: str, attr: int = 0) -> None:
        if y >= curses.LINES:
            return
        max_width = max(0, curses.COLS - x - 1)
        if max_width <= 0:
            return
        self.stdscr.addstr(y, x, text[:max_width], attr)


def _wrap(text: str, width: int) -> Iterable[str]:
    words = text.split()
    line = ""
    for word in words:
        next_line = word if not line else f"{line} {word}"
        if len(next_line) > width:
            if line:
                yield line
            line = word
        else:
            line = next_line
    if line:
        yield line
