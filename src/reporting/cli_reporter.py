from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

def print_accumulator_report(acc):
    if not acc:
        console.print("[bold red][!] Nessuna multipla generata con i criteri impostati.[/bold red]")
        return

    header_text = Text()
    header_text.append("FOOTSIGHT AI ", style="bold cyan")
    header_text.append("— ACCUMULATOR REPORT (MULTI-LEAGUE)\n", style="bold white")
    header_text.append(f"Quota Totale: {acc['total_odds']}  |  ", style="bold yellow")
    header_text.append(f"Prob. Combinata: {acc['combined_prob']}%  |  ", style="bold green")
    header_text.append(f"Expected Value (EV): +{acc['expected_value']}", style="bold magenta")

    console.print(Panel(header_text, border_style="cyan"))

    table = Table(title="Dettaglio Schedina Multipla Selezione Target", title_style="bold white")
    table.add_column("#", style="dim", width=3)
    table.add_column("Lega", style="cyan", width=8)
    table.add_column("Match", style="white", width=28)
    table.add_column("Esito", style="bold yellow", width=16)
    table.add_column("Quota", justify="right", style="bold magenta")
    table.add_column("Prob. Stima", justify="right", style="green")
    table.add_column("EV Single", justify="right", style="bold cyan")

    for idx, ev in enumerate(acc["events"], 1):
        table.add_row(
            str(idx),
            ev["league"],
            ev["match"],
            ev["selection"],
            f"{ev['odds']:.2f}",
            f"{ev['prob']*100:.1f}%",
            f"+{ev['ev']:.4f}"
        )

    console.print(table)
    console.print("[dim italic]* Garanzia Anti-Leakage: Probabilità stimate solo da dati antecedenti al match.[/dim italic]\n")

def print_singles_report(singles):
    if not singles:
        console.print("[bold red][!] Nessuna scommessa singola a valore (Quota <= 3.50) trovata.[/bold red]")
        return

    console.print(Panel("[bold cyan]FOOTSIGHT AI[/bold cyan] — [bold white]TOP VALUE BETS SINGOLE (STABILIZZATE)[/bold white]", border_style="green"))

    table = Table(title="Scommesse Singole Consigliate con Gestione Risk/Stake", title_style="bold white")
    table.add_column("#", style="dim", width=3)
    table.add_column("Lega", style="cyan", width=8)
    table.add_column("Match", style="white", width=28)
    table.add_column("Esito", style="bold yellow", width=16)
    table.add_column("Quota", justify="right", style="bold magenta")
    table.add_column("Prob. Stima", justify="right", style="green")
    table.add_column("Vantaggio", justify="right", style="bold yellow")
    table.add_column("EV", justify="right", style="bold cyan")
    table.add_column("Stake %", justify="right", style="bold green")

    for idx, s in enumerate(singles, 1):
        table.add_row(
            str(idx),
            s["league"],
            s["match"],
            s["selection"],
            f"{s['odds']:.2f}",
            f"{s['prob_est']*100:.1f}%",
            f"+{s['edge']*100:.1f}%",
            f"+{s['ev']:.4f}",
            f"{s['stake_pct']}%"
        )

    console.print(table)
    console.print("[dim italic]* Stake % = Frazione consigliata del Bankroll calcolata tramite il Criterio di Kelly Frazionato.[/dim italic]\n")

def print_tracker_summary(summary):
    console.print(Panel("[bold cyan]FOOTSIGHT AI[/bold cyan] — [bold white]BANKROLL & BETS PERFORMANCE TRACKER[/bold white]", border_style="magenta"))

    table = Table(title="Consuntivo Performance Reali", title_style="bold white")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valore", justify="right", style="bold yellow")

    table.add_row("Giocate Concluse", str(summary["total_settled"]))
    table.add_row("Giocate In Attesa", str(summary["pending"]))
    table.add_row("Totale Scommesso", f"{summary['total_staked']:.2f} €")
    
    prof_color = "green" if summary["total_profit"] >= 0 else "red"
    table.add_row("Profitto Netto", f"[{prof_color}]{summary['total_profit']:+.2f} €[/{prof_color}]")
    table.add_row("ROI % (Return on Investment)", f"[{prof_color}]{summary['roi_pct']:+.2f} %[/{prof_color}]")
    table.add_row("Win Rate %", f"{summary['win_rate_pct']:.1f} %")

    console.print(table)
    console.print("\n")
