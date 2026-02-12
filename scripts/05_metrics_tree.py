from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
import pandas as pd
import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "reports" / "metrics_tree"


@dataclass(frozen=True)
class Window:
    start: str
    end: str


@dataclass(frozen=True)
class MetricsTree:
    window: Window
    spend: float
    contacts: int
    calls: int
    deals: int
    paid_deals: int
    revenue_cash: float
    revenue_contract: float
    paid_rate: float | None
    cpl_deal: float | None
    cpa: float | None
    cash_roas: float | None
    contract_roas: float | None


def _ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "figures").mkdir(parents=True, exist_ok=True)


def _save_json(obj: object, name: str) -> None:
    (OUT_DIR / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT_DIR / "tables" / f"{name}.csv", index=False, encoding="utf-8")


def _require_clean() -> None:
    if not CLEAN_DIR.exists():
        raise SystemExit("Missing data/clean. Run scripts/01_clean_export.py first.")


def _date_range_from_series(series: pd.Series) -> tuple[date, date]:
    s = pd.to_datetime(series, errors="coerce")
    s = s.dropna()
    if len(s) == 0:
        raise ValueError("Cannot infer date range from empty series.")
    return s.min().date(), s.max().date()


def _safe_div(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return a / b


def _tree_from_frames(
    *,
    window_start: date,
    window_end: date,
    spend: pd.DataFrame,
    contacts: pd.DataFrame,
    calls: pd.DataFrame,
    deals: pd.DataFrame,
) -> MetricsTree:
    spend_w = spend[(spend["date"] >= window_start) & (spend["date"] <= window_end)]
    deals_w = deals.copy()
    deals_w["created_date"] = pd.to_datetime(deals_w["created_time"], errors="coerce").dt.date
    deals_w = deals_w[(deals_w["created_date"] >= window_start) & (deals_w["created_date"] <= window_end)]

    calls_w = calls.copy()
    calls_w["call_date"] = pd.to_datetime(calls_w["call_start_time"], errors="coerce").dt.date
    calls_w = calls_w[(calls_w["call_date"] >= window_start) & (calls_w["call_date"] <= window_end)]

    contacts_w = contacts.copy()
    contacts_w["created_date"] = pd.to_datetime(contacts_w["created_time"], errors="coerce").dt.date
    contacts_w = contacts_w[(contacts_w["created_date"] >= window_start) & (contacts_w["created_date"] <= window_end)]

    spend_sum = float(pd.to_numeric(spend_w["spend"], errors="coerce").fillna(0).sum())

    contacts_cnt = int(len(contacts_w))
    calls_cnt = int(len(calls_w))
    deals_cnt = int(len(deals_w))
    paid_cnt = int(deals_w["is_paid"].fillna(False).sum())

    revenue_cash = float(pd.to_numeric(deals_w["revenue_cash"], errors="coerce").fillna(0).sum())
    revenue_contract = float(pd.to_numeric(deals_w["revenue_contract"], errors="coerce").fillna(0).sum())

    paid_rate = _safe_div(paid_cnt, deals_cnt)
    cpl_deal = _safe_div(spend_sum, deals_cnt)
    cpa = _safe_div(spend_sum, paid_cnt)
    cash_roas = _safe_div(revenue_cash, spend_sum)
    contract_roas = _safe_div(revenue_contract, spend_sum)

    return MetricsTree(
        window=Window(start=str(window_start), end=str(window_end)),
        spend=spend_sum,
        contacts=contacts_cnt,
        calls=calls_cnt,
        deals=deals_cnt,
        paid_deals=paid_cnt,
        revenue_cash=revenue_cash,
        revenue_contract=revenue_contract,
        paid_rate=paid_rate,
        cpl_deal=cpl_deal,
        cpa=cpa,
        cash_roas=cash_roas,
        contract_roas=contract_roas,
    )


def _tree_by_source(
    *,
    window_start: date,
    window_end: date,
    spend: pd.DataFrame,
    deals: pd.DataFrame,
) -> pd.DataFrame:
    spend_w = spend[(spend["date"] >= window_start) & (spend["date"] <= window_end)].copy()
    spend_w["source"] = spend_w["source"].fillna("NA")

    deals_w = deals.copy()
    deals_w["created_date"] = pd.to_datetime(deals_w["created_time"], errors="coerce").dt.date
    deals_w = deals_w[(deals_w["created_date"] >= window_start) & (deals_w["created_date"] <= window_end)].copy()
    deals_w["source"] = deals_w["source"].fillna("NA")

    s = spend_w.groupby("source", dropna=False).agg(spend=("spend", "sum")).reset_index()
    d = (
        deals_w.groupby("source", dropna=False)
        .agg(
            deals=("deal_row_id", "size"),
            paid_deals=("is_paid", lambda x: int(x.fillna(False).sum())),
            revenue_cash=("revenue_cash", "sum"),
            revenue_contract=("revenue_contract", "sum"),
        )
        .reset_index()
    )

    m = s.merge(d, on="source", how="outer")
    for col in ["spend", "deals", "paid_deals", "revenue_cash", "revenue_contract"]:
        m[col] = pd.to_numeric(m[col], errors="coerce").fillna(0)

    m["paid_rate"] = m["paid_deals"] / m["deals"].replace(0, np.nan)
    m["cpl_deal"] = m["spend"] / m["deals"].replace(0, np.nan)
    m["cpa"] = m["spend"] / m["paid_deals"].replace(0, np.nan)
    m["cash_roas"] = m["revenue_cash"] / m["spend"].replace(0, np.nan)
    m["contract_roas"] = m["revenue_contract"] / m["spend"].replace(0, np.nan)

    return m.sort_values("spend", ascending=False)


def _format_money(x: float) -> str:
    """Format money with K/M suffix"""
    if x >= 1_000_000:
        return f"{x/1_000_000:.1f}M EUR"
    elif x >= 1_000:
        return f"{x/1_000:.0f}K EUR"
    else:
        return f"{x:.0f} EUR"


def _format_num(x: float) -> str:
    """Format large numbers with K suffix"""
    if x >= 1_000:
        return f"{x/1_000:.1f}K"
    else:
        return f"{x:.0f}"


def _create_sankey_diagram(tree: MetricsTree, title: str = "Metrics Tree") -> go.Figure:
    """
    Create Sankey diagram: Spend -> Deals -> Paid -> Revenue
    """
    # Nodes
    node_labels = [
        f"Spend<br>{_format_money(tree.spend)}",
        f"Deals<br>{_format_num(tree.deals)}",
        f"Paid<br>{tree.paid_deals}",
        f"Revenue<br>{_format_money(tree.revenue_contract)}",
    ]
    
    # Calculate flows
    flow_spend_deals = tree.spend
    flow_deals_paid = tree.spend * (tree.paid_rate if tree.paid_rate else 0)
    flow_paid_revenue = min(tree.revenue_contract, tree.spend * 3)
    
    # Links
    links = {
        'source': [0, 1, 2],
        'target': [1, 2, 3],
        'value': [flow_spend_deals, flow_deals_paid, flow_paid_revenue],
        'label': [
            f"CPL: {_format_money(tree.cpl_deal)}" if tree.cpl_deal else "CPL: N/A",
            f"Conv: {tree.paid_rate:.1%}" if tree.paid_rate else "Conv: N/A",
            f"ROAS: {tree.contract_roas:.1f}x" if tree.contract_roas else "ROAS: N/A",
        ]
    }
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=30,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=["#FF6B35", "#004E89", "#1B998B", "#2EC4B6"]
        ),
        link=dict(
            source=links['source'],
            target=links['target'],
            value=links['value'],
            label=links['label'],
            color=["rgba(255,107,53,0.3)", "rgba(0,78,137,0.3)", "rgba(27,153,139,0.3)"]
        )
    )])
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=20)),
        font=dict(size=12),
        height=400,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    
    return fig


def _create_revenue_decomposition_tree(tree: MetricsTree) -> plt.Figure:
    """
    Create Revenue decomposition tree (4 levels) - product analytics style
    
    Level 0: Revenue (North Star)
    Level 1: Volume (Paid Deals) × Value (AOV)
    Level 2: Deals × Paid Rate
    Level 3: Spend ÷ CPL
    """
    fig, ax = plt.subplots(figsize=(14, 12))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 14)
    ax.axis('off')
    
    # Calculate metrics
    aov = tree.revenue_contract / tree.paid_deals if tree.paid_deals > 0 else 0
    
    # Color scheme (like user's example)
    colors = {
        'north_star': '#9B59B6',  # Purple
        'drivers': '#E91E63',     # Pink dark
        'components': '#F48FB1',  # Pink light
        'inputs': '#FFE0B2'       # Beige
    }
    
    def draw_box(x, y, w, h, color, main_text, sub_text, text_color='white'):
        """Draw a rounded box with text"""
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.15",
            linewidth=2.5,
            edgecolor='#2C3E50',
            facecolor=color,
            alpha=0.9,
            zorder=2
        )
        ax.add_patch(rect)
        
        ax.text(
            x + w/2, y + h/2 + 0.2,
            main_text,
            ha='center', va='center',
            fontsize=16, fontweight='bold',
            color=text_color,
            zorder=3
        )
        
        ax.text(
            x + w/2, y + h/2 - 0.3,
            sub_text,
            ha='center', va='center',
            fontsize=13,
            color=text_color,
            zorder=3
        )
    
    def draw_arrow(x1, y1, x2, y2):
        """Draw arrow between boxes"""
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle='->,head_width=0.4,head_length=0.5',
            lw=2.5,
            color='#34495E',
            zorder=1
        )
        ax.add_patch(arrow)
    
    def draw_operator(x, y, text, size=16):
        """Draw mathematical operator"""
        ax.text(
            x, y, text,
            ha='center', va='center',
            fontsize=size, fontweight='bold',
            color='#2C3E50',
            bbox=dict(boxstyle='circle,pad=0.3', facecolor='white', edgecolor='#2C3E50', linewidth=2),
            zorder=3
        )
    
    # Level 0: North Star (Revenue)
    draw_box(4.5, 11, 5, 1.5, colors['north_star'],
             'Revenue (Contract)',
             f'{_format_money(tree.revenue_contract)}')
    
    # Arrow down
    draw_arrow(7, 11, 7, 10.2)
    
    # Operator: ×
    draw_operator(7, 9.8, '×', size=18)
    
    # Level 1: Volume × Value
    # Left: Paid Deals
    draw_box(1.5, 8, 4, 1.5, colors['drivers'],
             'Paid Deals',
             f'{tree.paid_deals:,}')
    
    # Right: AOV
    draw_box(8.5, 8, 4, 1.5, colors['drivers'],
             'AOV',
             f'{_format_money(aov)}')
    
    # Arrows to Line operator
    draw_arrow(3.5, 8, 5.5, 7.2)
    draw_arrow(10.5, 8, 8.5, 7.2)
    
    # Operator under Paid Deals: ×
    draw_operator(7, 6.8, '×', size=18)
    
    # Level 2: Deals × Paid Rate
    # Left: Deals
    draw_box(1.5, 5, 4, 1.5, colors['components'],
             'Deals',
             f'{tree.deals:,}',
             text_color='#2C3E50')
    
    # Right: Paid Rate
    draw_box(8.5, 5, 4, 1.5, colors['components'],
             'Paid Rate',
             f'{tree.paid_rate:.2%}' if tree.paid_rate else 'N/A',
             text_color='#2C3E50')
    
    # Arrows to next level
    draw_arrow(3.5, 5, 3.5, 4.2)
    
    # Operator under Deals: ÷
    draw_operator(3.5, 3.8, '÷', size=18)
    
    # Level 3: Spend ÷ CPL
    # Left: Spend
    draw_box(0.5, 2, 3, 1.5, colors['inputs'],
             'Spend',
             f'{_format_money(tree.spend)}',
             text_color='#2C3E50')
    
    # Right: CPL
    draw_box(4.5, 2, 3, 1.5, colors['inputs'],
             'CPL',
             f'{_format_money(tree.cpl_deal)}' if tree.cpl_deal else 'N/A',
             text_color='#2C3E50')
    
    # Title and legend
    ax.text(7, 13, 'Revenue Decomposition Tree', 
            ha='center', va='center',
            fontsize=20, fontweight='bold',
            color='#2C3E50')
    
    # Add legend boxes
    legend_y = 0.5
    legend_items = [
        (colors['north_star'], 'North Star'),
        (colors['drivers'], 'Drivers'),
        (colors['components'], 'Components'),
        (colors['inputs'], 'Inputs')
    ]
    
    for idx, (color, label) in enumerate(legend_items):
        x_pos = 9 + idx * 1.2
        rect = mpatches.Rectangle((x_pos, legend_y), 0.5, 0.4, 
                                   facecolor=color, edgecolor='#2C3E50', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x_pos + 0.6, legend_y + 0.2, label, 
                va='center', fontsize=10, color='#2C3E50')
    
    plt.tight_layout()
    return fig


def _create_roas_decomposition_tree(tree: MetricsTree) -> plt.Figure:
    """
    Create ROAS decomposition tree (3 levels) - marketing efficiency
    
    Level 0: ROAS (Marketing North Star)
    Level 1: Revenue ÷ Spend
    Level 2: (Paid × AOV) ÷ (Deals × CPL)
    """
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Calculate metrics
    aov = tree.revenue_contract / tree.paid_deals if tree.paid_deals > 0 else 0
    
    # Color scheme
    colors = {
        'north_star': '#9B59B6',  # Purple
        'drivers': '#E91E63',     # Pink dark
        'components': '#F48FB1',  # Pink light
    }
    
    def draw_box(x, y, w, h, color, main_text, sub_text, text_color='white'):
        """Draw a rounded box with text"""
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.15",
            linewidth=2.5,
            edgecolor='#2C3E50',
            facecolor=color,
            alpha=0.9,
            zorder=2
        )
        ax.add_patch(rect)
        
        ax.text(
            x + w/2, y + h/2 + 0.2,
            main_text,
            ha='center', va='center',
            fontsize=16, fontweight='bold',
            color=text_color,
            zorder=3
        )
        
        ax.text(
            x + w/2, y + h/2 - 0.3,
            sub_text,
            ha='center', va='center',
            fontsize=13,
            color=text_color,
            zorder=3
        )
    
    def draw_arrow(x1, y1, x2, y2):
        """Draw arrow between boxes"""
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle='->,head_width=0.4,head_length=0.5',
            lw=2.5,
            color='#34495E',
            zorder=1
        )
        ax.add_patch(arrow)
    
    def draw_operator(x, y, text, size=16):
        """Draw mathematical operator"""
        ax.text(
            x, y, text,
            ha='center', va='center',
            fontsize=size, fontweight='bold',
            color='#2C3E50',
            bbox=dict(boxstyle='circle,pad=0.3', facecolor='white', edgecolor='#2C3E50', linewidth=2),
            zorder=3
        )
    
    # Level 0: ROAS (North Star)
    draw_box(4.5, 9, 5, 1.5, colors['north_star'],
             'ROAS (Contract)',
             f'{tree.contract_roas:.2f}x' if tree.contract_roas else 'N/A')
    
    # Arrow down
    draw_arrow(7, 9, 7, 8.2)
    
    # Operator: ÷
    draw_operator(7, 7.8, '÷', size=18)
    
    # Level 1: Revenue ÷ Spend
    # Left: Revenue
    draw_box(1.5, 6, 4, 1.5, colors['drivers'],
             'Revenue',
             f'{_format_money(tree.revenue_contract)}')
    
    # Right: Spend
    draw_box(8.5, 6, 4, 1.5, colors['drivers'],
             'Spend',
             f'{_format_money(tree.spend)}')
    
    # Arrows to next level
    draw_arrow(3.5, 6, 3.5, 5.2)
    draw_arrow(10.5, 6, 10.5, 5.2)
    
    # Operators: × under each
    draw_operator(3.5, 4.8, '×', size=18)
    draw_operator(10.5, 4.8, '×', size=18)
    
    # Level 2 Left: Paid × AOV
    draw_box(0.5, 3, 2.8, 1.3, colors['components'],
             'Paid',
             f'{tree.paid_deals:,}',
             text_color='#2C3E50')
    
    draw_box(3.7, 3, 2.8, 1.3, colors['components'],
             'AOV',
             f'{_format_money(aov)}',
             text_color='#2C3E50')
    
    # Level 2 Right: Deals × CPL
    draw_box(7.7, 3, 2.8, 1.3, colors['components'],
             'Deals',
             f'{tree.deals:,}',
             text_color='#2C3E50')
    
    draw_box(10.9, 3, 2.8, 1.3, colors['components'],
             'CPL',
             f'{_format_money(tree.cpl_deal)}' if tree.cpl_deal else 'N/A',
             text_color='#2C3E50')
    
    # Title
    ax.text(7, 11, 'Marketing Efficiency: ROAS Decomposition', 
            ha='center', va='center',
            fontsize=20, fontweight='bold',
            color='#2C3E50')
    
    # Add formula box at bottom
    formula = f'ROAS = Revenue ÷ Spend = ({tree.paid_deals:,} × {_format_money(aov)}) ÷ ({tree.deals:,} × {_format_money(tree.cpl_deal) if tree.cpl_deal else "N/A"})'
    ax.text(7, 1.5, formula,
            ha='center', va='center',
            fontsize=11,
            color='#34495E',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#ECF0F1', edgecolor='#34495E', linewidth=1.5))
    
    # Growth levers box
    levers_text = 'Growth Levers:  ↓ CPL (better ads)  |  ↑ Paid Rate (better sales)  |  ↑ AOV (better products)'
    ax.text(7, 0.5, levers_text,
            ha='center', va='center',
            fontsize=10,
            color='#27AE60',
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#D5F4E6', edgecolor='#27AE60', linewidth=1.5))
    
    plt.tight_layout()
    return fig


def _create_block_schema(tree: MetricsTree, title: str = "Metrics Tree Schema"):
    """
    Create classic block schema with matplotlib
    """
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Define blocks
    blocks = [
        {
            'xy': (1, 9),
            'width': 8,
            'height': 1.5,
            'color': '#FF6B35',
            'main': f'Spend: {_format_money(tree.spend)}',
            'sub': f'CPL: {_format_money(tree.cpl_deal)}' if tree.cpl_deal else 'CPL: N/A'
        },
        {
            'xy': (1, 6.5),
            'width': 8,
            'height': 1.5,
            'color': '#004E89',
            'main': f'Deals: {_format_num(tree.deals)}',
            'sub': f'Paid rate: {tree.paid_rate:.2%}' if tree.paid_rate else 'Paid rate: N/A'
        },
        {
            'xy': (1, 4),
            'width': 8,
            'height': 1.5,
            'color': '#1B998B',
            'main': f'Paid: {tree.paid_deals}',
            'sub': f'CPA: {_format_money(tree.cpa)}' if tree.cpa else 'CPA: N/A'
        },
        {
            'xy': (1, 1.5),
            'width': 8,
            'height': 1.5,
            'color': '#2EC4B6',
            'main': f'Revenue: {_format_money(tree.revenue_contract)}',
            'sub': f'ROAS: {tree.contract_roas:.1f}x' if tree.contract_roas else 'ROAS: N/A'
        },
    ]
    
    # Draw blocks
    for block in blocks:
        rect = mpatches.FancyBboxPatch(
            block['xy'], block['width'], block['height'],
            boxstyle="round,pad=0.1",
            linewidth=2,
            edgecolor='black',
            facecolor=block['color'],
            alpha=0.7
        )
        ax.add_patch(rect)
        
        ax.text(
            block['xy'][0] + block['width']/2,
            block['xy'][1] + block['height']/2 + 0.3,
            block['main'],
            ha='center', va='center',
            fontsize=14, fontweight='bold',
            color='white'
        )
        
        ax.text(
            block['xy'][0] + block['width']/2,
            block['xy'][1] + block['height']/2 - 0.3,
            block['sub'],
            ha='center', va='center',
            fontsize=11,
            color='white'
        )
    
    # Draw arrows
    arrow_props = dict(arrowstyle='->', lw=2.5, color='black')
    arrows = [
        ((5, 9), (5, 8)),
        ((5, 6.5), (5, 5.5)),
        ((5, 4), (5, 3)),
    ]
    
    for start, end in arrows:
        ax.annotate('', xy=end, xytext=start, arrowprops=arrow_props)
    
    ax.text(5, 11.5, title, ha='center', va='top', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    return fig


def _create_sankey_by_source(tree_df: pd.DataFrame, source_name: str) -> go.Figure:
    """Create Sankey for a specific source"""
    row = tree_df[tree_df['source'] == source_name].iloc[0]
    
    node_labels = [
        f"Spend<br>{_format_money(row['spend'])}",
        f"Deals<br>{_format_num(row['deals'])}",
        f"Paid<br>{int(row['paid_deals'])}",
        f"Revenue<br>{_format_money(row['revenue_contract'])}",
    ]
    
    flow_spend_deals = row['spend']
    flow_deals_paid = row['spend'] * (row['paid_rate'] if not pd.isna(row['paid_rate']) else 0)
    flow_paid_revenue = min(row['revenue_contract'], row['spend'] * 3)
    
    links = {
        'source': [0, 1, 2],
        'target': [1, 2, 3],
        'value': [flow_spend_deals, flow_deals_paid, flow_paid_revenue],
    }
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=["#FF6B35", "#004E89", "#1B998B", "#2EC4B6"]
        ),
        link=dict(
            source=links['source'],
            target=links['target'],
            value=links['value'],
            color=["rgba(255,107,53,0.3)", "rgba(0,78,137,0.3)", "rgba(27,153,139,0.3)"]
        )
    )])
    
    fig.update_layout(
        title=dict(text=f"Metrics Tree: {source_name}", font=dict(size=16)),
        font=dict(size=10),
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    return fig


def main() -> None:
    _ensure_dirs()
    _require_clean()

    contacts = pd.read_parquet(CLEAN_DIR / "contacts.parquet")
    calls = pd.read_parquet(CLEAN_DIR / "calls.parquet")
    deals = pd.read_parquet(CLEAN_DIR / "deals.parquet")
    spend = pd.read_parquet(CLEAN_DIR / "spend.parquet")

    spend_start, spend_end = _date_range_from_series(spend["date"])
    deals_start, deals_end = _date_range_from_series(deals["created_time"])

    overlap_start = max(spend_start, deals_start)
    overlap_end = min(spend_end, deals_end)

    overall_full = _tree_from_frames(
        window_start=min(spend_start, deals_start),
        window_end=max(spend_end, deals_end),
        spend=spend,
        contacts=contacts,
        calls=calls,
        deals=deals,
    )
    overall_overlap = _tree_from_frames(
        window_start=overlap_start,
        window_end=overlap_end,
        spend=spend,
        contacts=contacts,
        calls=calls,
        deals=deals,
    )

    _save_json(asdict(overall_full), "metrics_tree_overall_full_window")
    _save_json(asdict(overall_overlap), "metrics_tree_overall_overlap_window")

    by_source = _tree_by_source(window_start=overlap_start, window_end=overlap_end, spend=spend, deals=deals)
    _save_csv(by_source, "metrics_tree_by_source_overlap_window")

    notes = {
        "lead_definition": "В дереве метрик deals считаются как основной прокси-объём (созданные сделки). Contacts/Calls показаны справочно.",
        "id_caveat": "Точные связи Contacts-Calls-Deals ограничены из-за Excel float; поэтому дерево не строится по contact-level конверсиям.",
        "windows": {
            "spend": {"start": str(spend_start), "end": str(spend_end)},
            "deals_created": {"start": str(deals_start), "end": str(deals_end)},
            "overlap": {"start": str(overlap_start), "end": str(overlap_end)},
        },
    }
    _save_json(notes, "notes")

    # Generate visualizations
    print("[INFO] Generating Sankey diagram (overall)...")
    sankey_overall = _create_sankey_diagram(
        overall_overlap,
        title="Metrics Tree: Overall (Overlap Window)"
    )
    sankey_overall.write_image(str(OUT_DIR / "figures" / "sankey_overall.png"), width=1000, height=500)
    sankey_overall.write_html(str(OUT_DIR / "figures" / "sankey_overall.html"))
    
    print("[INFO] Generating block schema (overall)...")
    schema_fig = _create_block_schema(
        overall_overlap,
        title="Metrics Tree: Spend -> Deals -> Paid -> Revenue"
    )
    schema_fig.savefig(OUT_DIR / "figures" / "tree_schema.png", dpi=150, bbox_inches='tight')
    plt.close(schema_fig)
    
    print("[INFO] Generating Revenue decomposition tree (4 levels)...")
    revenue_tree_fig = _create_revenue_decomposition_tree(overall_overlap)
    revenue_tree_fig.savefig(OUT_DIR / "figures" / "tree_revenue_decomposition.png", dpi=150, bbox_inches='tight')
    plt.close(revenue_tree_fig)
    
    print("[INFO] Generating ROAS decomposition tree (3 levels)...")
    roas_tree_fig = _create_roas_decomposition_tree(overall_overlap)
    roas_tree_fig.savefig(OUT_DIR / "figures" / "tree_roas_decomposition.png", dpi=150, bbox_inches='tight')
    plt.close(roas_tree_fig)
    
    # Generate Sankey for top-5 sources
    print("[INFO] Generating Sankey diagrams for top-5 sources...")
    top5_sources = by_source.head(5)
    for idx, row in top5_sources.iterrows():
        source = row['source']
        safe_name = source.replace(" ", "_").replace("/", "_")
        
        sankey_src = _create_sankey_by_source(by_source, source)
        sankey_src.write_image(
            str(OUT_DIR / "figures" / f"sankey_by_source_{safe_name}.png"),
            width=800,
            height=400
        )
        sankey_src.write_html(
            str(OUT_DIR / "figures" / f"sankey_by_source_{safe_name}.html")
        )
    
    print("[OK] reports/metrics_tree ready (JSON + tables + visualizations)")


if __name__ == "__main__":
    main()

