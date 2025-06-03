from pydantic import BaseModel
from typing import Literal, Self, Tuple
import re
import rich
from rich.table import Table

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


def get_diff(en_article: Article, translation_article: Article) -> Tuple[bool, Table]:
    table = Table(title="diff", show_lines=True)
    table.add_column("Original", overflow="fold")
    table.add_column("Translation", overflow="fold")

    success: bool = True

    tr_index = 0
    en_index = 0

    def en() -> TextEntry:
        return en_article.texts[en_index]

    def tr() -> TextEntry:
        return translation_article.texts[tr_index]

    while tr_index < len(translation_article.texts) and en_index < len(
        en_article.texts
    ):
        if en().color == "0" and tr().color == "0":
            # Both are normal text and accepted.
            table.add_row(format_text(en()), format_text(tr()))
            en_index += 1
            tr_index += 1

        elif en().color == "0" and tr().color != "0":
            # en() is normal text, tr() is not.
            table.add_row(format_text(en(), style="yellow", is_color_all=True), "")
            en_index += 1
        elif en().color != "0" and tr().color == "0":
            # en() is not normal text, tr() is normal text.
            table.add_row("", format_text(tr(), style="yellow", is_color_all=True))
            tr_index += 1
        else:
            # both are not normal text.
            if en().color == tr().color:
                table.add_row(format_text(en()), format_text(tr()))
                en_index += 1
                tr_index += 1
            else:
                table.add_row(
                    format_text(en(), style="red bold", is_color_all=False),
                    format_text(tr(), style="green bold", is_color_all=False),
                )
                en_index += 1
                tr_index += 1
                success = False

    while tr_index < len(translation_article.texts):
        if tr().color == "0":
            table.add_row("", format_text(tr(), style="yellow", is_color_all=True))
        else:
            table.add_row("", format_text(tr(), style="red bold", is_color_all=False))
            success = False
        tr_index += 1

    while en_index < len(en_article.texts):
        if en().color == "0":
            table.add_row(format_text(en(), style="yellow", is_color_all=True), "")
        else:
            table.add_row(format_text(en(), style="red bold", is_color_all=False), "")
            success = False
        en_index += 1

    return success, table


def main():
    rich.print("[bold]Hello from minecraft-questboook-format-checker![/bold]")
    # en_raw = input_until_not_empty("Enter the original article: ")
    # translation_raw = input_until_not_empty("Enter the translated article: ")
    en_raw = "There are two main types of §3Fission Reactors§r: §aBreeder§r and §aPower§r reactors. A breeder reactor is a reactor optimized to generate §bfission products the fastest§r. A power reactor, on the other hand, is optimized to generate the §bmost power it can§r.%n%nWhilst technically, power reactors are also very good at breeding, their design and maintenance is usually §emore involved§r. So, in fission reactions where you use power reactors, you do not need a breeder reactor for that reacion. §cBreeder Reactors generally produce very little power!§r%n%nYou will need at least one breeder reactor, but whether you pursue power generation is up to you. §eHowever, Fission Reactors are a good power source, and can greatly improve power stability!§r%n%nA breeder reactor's only important factors are §ahow much reactor cells it has§r, and §astaying heat neutral/negative§r. A reactor with two times more reactor cells will generate two times more fission products as long as they are both heat neutral.%n%nThe most common design for a breeder reactor is the §9Cryolattice§r, explained in the following quests. While this is not the most efficient, as using §eActive Cooling§r can improve your efficiency, constantly consuming coolant may not be preferred, and breeder reactors do not need active coolers to produce products fast.%n%nHowever, a power focused reactor has many more considerations, including considering the balance of §6Reactor Cells§r and §6Moderator Blocks§r, to improve §afuel efficiency§r, §astaying heat neutral/negative§r and §amaximize power generation§r. Because of the extra heat generated by moderator blocks, power reactors should pretty much always use active cooling, making them §cmore expensive to maintain§r. These extra considerations also mean there is no easy optimal design.%n%nFor power reactors in Nomi-CEu, you probably want to focus on using §eTBU Fuel§r, through §6Thorium§r obtained through processing §bBlack Granite§r.%n%nYou can also combine this with another reactor that uses §eLEU-233 Fuel§r. This is made with §6Uranium 233§r, obtained from §bTBU Recycling§r, and §6Uranium 238§r, from processing §bRed Granite§r.%n%nLEU-233 can generate a lot more energy, but needs more supporting infrastructure. If you want to have a LEU-233 power reactor, you probably want to setup a TBU power reactor first, to build up your Uranium-233 supply.%n%nTo plan these, you will need an alternative rather than a guide... maybe a reactor planner, or a reactor generator? Check out the following quests.%n%nAlso, planning reactors and then pasting them can be faster than building them, even for breeders! Check out the following quests even if you aren't planning a power focused reactor."
    translation_raw = "§3裂变反应堆§r共有两种：§a增殖反应堆§r和§a产能反应堆§r。增殖反应堆能§b以最快速度产出裂变产物§r，产能反应堆则能§b产出最多能量§r。%n%n同时，从技术上说，产能反应堆的增殖性能也很强，但可能在设计和维护上需要§e耗费更多精力§r。因而，若你制作了某一反应的产能反应堆，则无需再制作一个增殖反应堆。§c增殖反应堆的产能通常非常低！§r%n%n你至少需要一个增殖反应堆，产能反应堆则是可选项。§e即使如此，裂变反应堆仍然是极佳的产能来源，且能极大地提升发电稳定性！§r%n%n对增殖反应堆来说，唯一重要的是§a有多少反应堆单元§r，以及§a是否能保持热中性/热负性§r。具有两倍反应堆单元的反应堆将产生两倍的裂变产物，只要它们都保持热中性。%n%n增殖反应堆最常见的设计是§9凛冰晶格§r，将在接下来的任务中详细说明。虽然使用§e主动冷却§r可以提高效率，但持续消耗冷却剂可能并不可取，而且增殖反应堆不需要主动冷却器也能快速产出产物。%n%n然而，以发电为重点的反应堆需要考虑更多因素，包括平衡§6反应堆单元§r和§6慢化剂方块§r的比例，以提高§a燃料效率§r，§a保持热中性/热负性§r以及§a最大化发电量§r。由于慢化剂方块产生的额外热量，产能反应堆几乎总是需要使用主动冷却，这使得它们§c维护成本更高§r。这些额外的考虑因素也意味着没有简单的最优设计。%n%n对于Nomi-CEu中的产能反应堆，你可能需要专注于使用§eTBU燃料§r，这种燃料通过处理§b黑花岗岩§r获得的§6钍§r制造。%n%n你也可以将其与使用§eLEU-233燃料§r的另一个反应堆结合使用。这种燃料是用§bTBU回收§r获得的§6铀-233§r和处理§b红花岗岩§r得到的§6铀-238§r制成的。%n%nLEU-233能产生更多的能量，但需要更多的支持基础设施。如果你想要建造LEU-233产能反应堆，你可能需要先建立一个TBU产能反应堆，以积累铀-233储备。%n%n要规划这些反应堆，你需要一个本任务书之外的替代方案……也许是反应堆规划器或反应堆生成器？查看接下来的任务了解详情。%n%n另外，即使是对于增殖反应堆来说，规划反应堆然后粘贴建造也可能比直接建造更快！即使你不打算建造以发电为重点的反应堆，也请查看接下来的任务。"
    en_article = Article.parse_questbook_string(en_raw)
    translation_article = Article.parse_questbook_string(translation_raw)

    success, table = get_diff(en_article, translation_article)
    if success:
        rich.print("[green]Articles are consistent![/green]")
    else:
        rich.print("[red]Articles are not consistent![/red]")
    rich.print(table)


if __name__ == "__main__":
    main()
