from enum import Enum
from pydantic import BaseModel
from typing import Literal, Self, Tuple
import re
import rich
from rich.table import Table
import typer
from pathlib import Path

STYLE_CODES = [
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "ENDLINE",
    "k",
    "l",
    "m",
    "n",
    "o",
    "r",
]

type Color = Literal[
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "ENDLINE",
    "k",
    "l",
    "m",
    "n",
    "o",
    "r",
]


class TextEntry(BaseModel):
    color: Color
    content: str


class Article(BaseModel):
    texts: list[TextEntry]

    @classmethod
    def parse_questbook_string(cls, raw_article: str) -> Self:
        texts: list[TextEntry] = []

        text_lines = raw_article.split("%n")
        for line in text_lines:
            invalid_matches = re.findall(r"%(.)", line)
            for match in invalid_matches:
                if match[0] not in ["n", "%"]:
                    rich.print(
                        f'[red]Invalid matches: "%{match[0]}" in line "{line}"[/red]'
                    )
                    raise ValueError(f'Invalid matches: "%{match[0]}"')

            invalid_matches = re.findall(r"§(.)", line)
            for match in invalid_matches:
                if match[0] not in STYLE_CODES:
                    rich.print(
                        f'[red]Invalid matches: "§{match[0]}" in line "{line}"[/red]'
                    )
                    raise ValueError(f'Invalid matches: "§{match[0]}"')

            if texts:
                texts.append(TextEntry(color="ENDLINE", content="%n"))

            current_color: Color = "0"

            text_matches = re.findall(r"(§[0-9a-fr])|([^§]+)", line)
            for match in text_matches:
                if match[0]:
                    if match[0][1] == "r":
                        current_color = "0"
                    else:
                        current_color = match[0][1]
                else:
                    texts.append(TextEntry(color=current_color, content=match[1]))

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
        if text.color == "ENDLINE":
            return f"[{style}]{text.content}[/{style}]" if style else text.content

        color_as_str: str = f"§{text.color}"
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
        if a().color == "0" and b().color == "0":
            # Both are normal text and accepted.
            table.add_row(format_text(a()), format_text(b()))
            index_1 += 1
            index_2 += 1

        elif a().color == "0" and b().color != "0":
            # en() is normal text, tr() is not.
            table.add_row(format_text(a(), style="yellow", is_color_all=True), "")
            index_1 += 1

        elif a().color != "0" and b().color == "0":
            # en() is not normal text, tr() is normal text.
            table.add_row("", format_text(b(), style="yellow", is_color_all=True))
            index_2 += 1

        else:
            # both are not normal text.
            if a().color == b().color:
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
        if b().color == "0":
            table.add_row("", format_text(b(), style="yellow", is_color_all=True))
        else:
            table.add_row("", format_text(b(), style="red bold", is_color_all=False))
            success = False
        index_2 += 1

    while index_1 < len(article_1.texts):
        if a().color == "0":
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
