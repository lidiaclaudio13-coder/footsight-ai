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
    header_text.append(f"Quota Totale: {acc.get('total_odds', 0.0)}  |  ", style="bold yellow")
    header_text.append(f"Prob. Combinata: {acc.get('combined_prob', 0.0)}%  |  ", style="bold green")
    header_text.append(f"Expected Value (EV): +{acc.get('expected_value', 0.0)}", style="bold magenta")

    console.print(Panel(header_text, border_style="cyan"))

    table = Table(title="Dettaglio Schedina Multipla Selezione Target", title_style="bold white")
    table.add_column("#", style="dim", width=3)
    table.add_column("Lega", style="cyan", width=8)
    table.add_column("Match", style="white", width=28)
    table.add_column("Esito", style="bold yellow", width=16)
    table.add_column("Quota", justify="right", style="bold magenta")
    table.add_column("Prob. Stima", justify="right", style="green")
    table.add_column("EV Single", justify="right", style="bold cyan")

    for idx, ev in enumerate(acc.get("events", []), 1):
        ev_val = float(ev.get("ev", ev.get("expected_value", 0.0)))
        odds_val = float(ev.get("odds", 1.0))
        prob_val = float(ev.get("prob", 0.0))

        table.add_row(
            str(idx),
            str(ev.get("league", "N/A")),
            str(ev.get("match", "N/A")),
            str(ev.get("selection", "N/A")),
            f"{odds_val:.2f}",
            f"{prob_val * 100:.1f}%",
            f"+{ev_val:.4f}"
        )

    console.print(table)
    console.print("[dim italic]* Garanzia Anti-Leakage: Probabilità stimate solo da dati antecedenti al match.[/dim italic]\n")

def print_singles_report(singles):
    if not singles:
        console.print("[bold red][!] Nessuna scommessa singola a valore trovata.[/bold red]")
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
        odds_val = float(s.get("odds", 1.0))
        prob_val = float(s.get("prob_est", 0.0))
        edge_val = float(s.get("edge", 0.0))
        ev_val = float(s.get("ev", 0.0))

        table.add_row(
            str(idx),
            str(s.get("league", "N/A")),
            str(s.get("match", "N/A")),
            str(s.get("selection", "N/A")),
            f"{odds_val:.2f}",
            f"{prob_val * 100:.1f}%",
            f"+{edge_val * 100:.1f}%",
            f"+{ev_val:.4f}",
            f"{s.get('stake_pct', 0.0)}%"
        )

    console.print(table)
    console.print("[dim italic]* Stake % = Frazione consigliata del Bankroll calcolata tramite il Criterio di Kelly Frazionato.[/dim italic]\n")

def print_tracker_summary(summary):
    console.print(Panel("[bold cyan]FOOTSIGHT AI[/bold cyan] — [bold white]BANKROLL & BETS PERFORMANCE TRACKER[/bold white]", border_style="magenta"))

    table = Table(title="Consuntivo Performance Reali", title_style="bold white")
    table.add_column("Metrica", style="cyan")
    table.add_column("Valore", justify="right", style="bold yellow")

    table.add_row("Giocate Concluse", str(summary.get("total_settled", 0)))
    table.add_row("Giocate In Attesa", str(summary.get("pending", 0)))
    table.add_row("Totale Scommesso", f"{float(summary.get('total_staked', 0.0)):.2f} €")
    
    total_profit = float(summary.get("total_profit", 0.0))
    prof_color = "green" if total_profit >= 0 else "red"
    table.add_row("Profitto Netto", f"[{prof_color}]{total_profit:+.2f} €[/{prof_color}]")
    table.add_row("ROI % (Return on Investment)", f"[{prof_color}]{float(summary.get('roi_pct', 0.0)):+.2f} %[/{prof_color}]")
    table.add_row("Win Rate %", f"{float(summary.get('win_rate_pct', 0.0)):.1f} %")

    console.print(table)
    console.print("\n")