from enum import Enum
from pydantic import BaseModel
from typing import Self, Tuple
import re
import rich
from rich.table import Table
import typer
from pathlib import Path

CODE_OBFUSCATED = "k"
CODE_BOLD = "l"
CODE_STRIKETHROUGH = "m"
CODE_UNDERLINE = "n"
CODE_ITALIC = "o"
CODE_RESET = "r"

STYLE_CODES = (
    "0123456789abcdef"
    + CODE_OBFUSCATED
    + CODE_BOLD
    + CODE_STRIKETHROUGH
    + CODE_UNDERLINE
    + CODE_ITALIC
    + CODE_RESET
)


class TextStyle(BaseModel):
    color: str = "0"
    is_bold: bool = False
    is_italic: bool = False
    is_underline: bool = False
    is_strikethrough: bool = False
    is_obfuscated: bool = False


class TextEntry(BaseModel):
    style: TextStyle
    content: str

    def can_be_ignored(self) -> bool:
        return self.style.color == "0"


class Article(BaseModel):
    texts: list[TextEntry]

    @staticmethod
    def raise_if_invalid(raw_article: str) -> None:
        invalid_matches = re.findall(r"%(.)", raw_article)
        for match in invalid_matches:
            if match[0] not in ["n", "%"]:
                rich.print(f'[red]Invalid matches: "%{match[0]}"[/red]')
                raise ValueError(f'Invalid matches: "%{match[0]}"')

        invalid_matches = re.findall(r"§(.)", raw_article)
        for match in invalid_matches:
            if match[0] not in STYLE_CODES:
                rich.print(f'[red]Invalid matches: "§{match[0]}"[/red]')
                raise ValueError(f'Invalid matches: "§{match[0]}"')

    @classmethod
    def parse_questbook_string(cls, raw_article: str) -> Self:
        cls.raise_if_invalid(raw_article)

        texts: list[TextEntry] = []

        text_lines = raw_article.split("%n")
        for line in text_lines:
            if texts:
                texts.append(TextEntry(style=TextStyle(color="ENDLINE"), content="%n"))

            current_color: str = "0"

            text_matches = re.findall(r"(§[0-9a-fr])|([^§]+)", line)
            for match in text_matches:
                if match[0]:
                    if match[0][1] == "r":
                        current_color = "0"
                    else:
                        current_color = match[0][1]
                else:
                    texts.append(
                        TextEntry(
                            style=TextStyle(color=current_color), content=match[1]
                        )
                    )

        return cls(texts=texts)


def input_until_not_empty(prompt: str) -> str:
    while True:
        user_input = input(prompt)
        if user_input:
            return user_input


def format_text(
    text: TextEntry | None, style: str | None = None, *, is_color_all: bool = True
) -> str:
    if isinstance(text, TextEntry):
        if text.style.color == "ENDLINE":
            return f"[{style}]{text.content}[/{style}]" if style else text.content

        color_as_str: str = f"§{text.style.color}"
        content_as_str: str = text.content

        if style is not None:
            if is_color_all:
                return f"[{style}]{color_as_str}{content_as_str}[/{style}]"
            else:
                return f"[{style}]{color_as_str}[/{style}]{content_as_str}"
        else:
            return f"{color_as_str}{content_as_str}"
    else:
        return f"[{style}]{str(text)}[/{style}]" if style else str(text)


def get_diff(article_1: Article, article_2: Article) -> Tuple[bool, Table]:
    table = Table(title="diff", show_lines=True)
    table.add_column("Article 1", overflow="fold")
    table.add_column("Article 2", overflow="fold")

    success: bool = True

    index_1 = 0
    index_2 = 0

    def a() -> TextEntry:
        return article_1.texts[index_1]

    def b() -> TextEntry:
        return article_2.texts[index_2]

    while index_1 < len(article_1.texts) and index_2 < len(article_2.texts):
        if a().can_be_ignored() and b().can_be_ignored():
            # Both are normal text and accepted.
            table.add_row(format_text(a()), format_text(b()))
            index_1 += 1
            index_2 += 1

        elif a().can_be_ignored() and not b().can_be_ignored():
            # en() is normal text, tr() is not.
            table.add_row(format_text(a(), style="yellow", is_color_all=True), "")
            index_1 += 1

        elif not a().can_be_ignored() and b().can_be_ignored():
            # en() is not normal text, tr() is normal text.
            table.add_row("", format_text(b(), style="yellow", is_color_all=True))
            index_2 += 1

        else:
            # both are not normal text.
            if a().style == b().style:
                table.add_row(format_text(a()), format_text(b()))
            else:
                table.add_row(
                    format_text(a(), style="red bold", is_color_all=False),
                    format_text(b(), style="green bold", is_color_all=False),
                )
                success = False
            index_1 += 1
            index_2 += 1

    while index_2 < len(article_2.texts):
        if b().style.color == "0":
            table.add_row("", format_text(b(), style="yellow", is_color_all=True))
        else:
            table.add_row("", format_text(b(), style="red bold", is_color_all=False))
            success = False
        index_2 += 1

    while index_1 < len(article_1.texts):
        if a().style.color == "0":
            table.add_row(format_text(a(), style="yellow", is_color_all=True), "")
        else:
            table.add_row(format_text(a(), style="red bold", is_color_all=False), "")
            success = False
        index_1 += 1

    return success, table


app = typer.Typer()


class ShowTableEnum(str, Enum):
    ALWAYS = "always"
    ON_ERROR = "on_error"
    NEVER = "never"


@app.command()
def main(
    file1: Path, file2: Path, *, show_table: ShowTableEnum = ShowTableEnum.ON_ERROR
):
    file1_raw = file1.read_text(encoding="utf-8")
    file2_raw = file2.read_text(encoding="utf-8")

    article1 = Article.parse_questbook_string(file1_raw)
    article2 = Article.parse_questbook_string(file2_raw)

    success, table = get_diff(article1, article2)
    if success:
        rich.print("[green]Articles are consistent![/green]")
        if show_table == ShowTableEnum.ALWAYS:
            rich.print(table)
    else:
        rich.print("[red]Articles are not consistent![/red]")
        if show_table in [ShowTableEnum.ALWAYS, ShowTableEnum.ON_ERROR]:
            rich.print(table)


if __name__ == "__main__":
    app()
