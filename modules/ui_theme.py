import streamlit as st


PALETTE = {
    "primary": "#da291c",
    "primary_active": "#b01e0a",
    "primary_hover": "#9d2211",
    "canvas": "#181818",
    "canvas_elevated": "#303030",
    "canvas_light": "#f7f7f7",
    "ink": "#ffffff",
    "body": "#b3b3b3",
    "body_strong": "#ffffff",
    "body_on_light": "#181818",
    "muted": "#8f8f8f",
    "hairline": "#3a3a3a",
    "hairline_soft": "#4a4a4a",
    "success": "#03904a",
    "warning": "#f13a2c",
    "info": "#4c98b9",
}


SPACING = {
    "xxxs": "4px",
    "xxs": "8px",
    "xs": "16px",
    "sm": "24px",
    "md": "32px",
    "lg": "48px",
    "xl": "64px",
    "xxl": "96px",
}


GLOBAL_CSS = f"""
<style>
    :root {{
        --brand-primary: {PALETTE['primary']};
        --brand-primary-active: {PALETTE['primary_active']};
        --brand-primary-hover: {PALETTE['primary_hover']};
        --brand-canvas: {PALETTE['canvas']};
        --brand-surface: {PALETTE['canvas_elevated']};
        --brand-surface-light: {PALETTE['canvas_light']};
        --brand-ink: {PALETTE['ink']};
        --brand-body: {PALETTE['body']};
        --brand-body-strong: {PALETTE['body_strong']};
        --brand-body-on-light: {PALETTE['body_on_light']};
        --brand-muted: {PALETTE['muted']};
        --brand-hairline: {PALETTE['hairline']};
        --brand-hairline-soft: {PALETTE['hairline_soft']};
        --brand-success: {PALETTE['success']};
        --brand-warning: {PALETTE['warning']};
        --brand-info: {PALETTE['info']};
        --space-xxs: {SPACING['xxs']};
        --space-xs: {SPACING['xs']};
        --space-sm: {SPACING['sm']};
        --space-md: {SPACING['md']};
        --space-lg: {SPACING['lg']};
        --space-xl: {SPACING['xl']};
        --space-xxl: {SPACING['xxl']};
        --font-display: "Helvetica Neue", "Arial Narrow", Arial, sans-serif;
        --font-body: "Avenir Next", "Segoe UI", sans-serif;
    }}

    .stApp {{
        background:
            radial-gradient(circle at top right, rgba(218, 41, 28, 0.16), transparent 24%),
            linear-gradient(180deg, rgba(60,60,60,0.16), rgba(3,3,3,0) 22%),
            var(--brand-canvas);
        color: var(--brand-ink);
        font-family: var(--font-body);
    }}

    .block-container {{
        padding-top: 0 !important;
        padding-bottom: var(--space-xl) !important;
        max-width: 1280px !important;
    }}

    [data-testid="stSidebar"] {{
        background: rgba(24, 24, 24, 0.98);
        border-right: 1px solid var(--brand-hairline);
    }}

    [data-testid="stSidebar"] * {{
        color: var(--brand-ink);
    }}

    h1, h2, h3, h4 {{
        font-family: var(--font-display);
        letter-spacing: -0.02em;
        font-weight: 500;
    }}

    p, label, li, div[data-testid="stMarkdownContainer"] p {{
        font-family: var(--font-body);
    }}

    .brand-hero {{
        position: relative;
        overflow: hidden;
        margin: 0 calc(-1 * var(--space-sm)) var(--space-lg);
        padding: 120px var(--space-lg) 88px;
        min-height: 56vh;
        display: flex;
        align-items: end;
        background:
            linear-gradient(180deg, rgba(24,24,24,0.18), rgba(24,24,24,0.92)),
            linear-gradient(135deg, rgba(218, 41, 28, 0.22), transparent 42%),
            radial-gradient(circle at 85% 18%, rgba(255,255,255,0.12), transparent 18%),
            radial-gradient(circle at 18% 24%, rgba(218,41,28,0.18), transparent 24%),
            linear-gradient(120deg, #202020 0%, #111111 38%, #2e2e2e 100%);
        border-bottom: 1px solid var(--brand-hairline);
    }}

    .brand-hero::after {{
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, rgba(24,24,24,0.78) 0%, rgba(24,24,24,0.34) 45%, rgba(24,24,24,0.72) 100%);
        pointer-events: none;
    }}

    .brand-hero__content {{
        position: relative;
        z-index: 1;
        max-width: 760px;
    }}

    .brand-eyebrow {{
        display: inline-block;
        margin-bottom: var(--space-xs);
        padding: 6px 12px;
        border: 1px solid rgba(255,255,255,0.28);
        border-radius: 999px;
        font-size: 11px;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--brand-ink);
        background: rgba(255,255,255,0.06);
    }}

    .brand-hero h1 {{
        margin: 0;
        font-size: clamp(2.8rem, 6vw, 5rem);
        line-height: 1.02;
        color: var(--brand-ink);
    }}

    .brand-hero p {{
        margin: var(--space-sm) 0 0;
        max-width: 640px;
        color: #e0e0e0;
        font-size: 1rem;
        line-height: 1.75;
    }}

    .brand-strip {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: var(--space-xs);
        margin: calc(-1 * var(--space-md)) 0 var(--space-lg);
        position: relative;
        z-index: 4;
    }}

    .brand-metric {{
        padding: var(--space-sm);
        background: rgba(48, 48, 48, 0.9);
        border: 1px solid var(--brand-hairline);
        backdrop-filter: blur(10px);
    }}

    .brand-metric__label {{
        display: block;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: var(--brand-muted);
        margin-bottom: 8px;
    }}

    .brand-metric__value {{
        display: block;
        font-family: var(--font-display);
        font-size: 1.25rem;
        color: var(--brand-ink);
    }}

    .brand-section {{
        margin: 0 0 var(--space-lg);
        padding: var(--space-md);
        background: rgba(48, 48, 48, 0.62);
        border: 1px solid var(--brand-hairline);
    }}

    .brand-section--light {{
        background: rgba(247, 247, 247, 0.95);
        color: var(--brand-body-on-light);
        border-color: #d6d6d6;
    }}

    .brand-section__eyebrow {{
        margin: 0 0 10px;
        color: var(--brand-primary);
        font-size: 11px;
        letter-spacing: 0.24em;
        text-transform: uppercase;
    }}

    .brand-section__title {{
        margin: 0;
        font-size: clamp(1.5rem, 2.2vw, 2.35rem);
        line-height: 1.15;
    }}

    .brand-section__desc {{
        margin: 14px 0 0;
        max-width: 720px;
        color: var(--brand-body);
        line-height: 1.7;
    }}

    .brand-section--light .brand-section__desc,
    .brand-section--light .brand-section__title {{
        color: var(--brand-body-on-light);
    }}

    .brand-card {{
        padding: var(--space-sm);
        background: rgba(24, 24, 24, 0.74);
        border: 1px solid var(--brand-hairline);
        height: 100%;
    }}

    .brand-card--light {{
        background: rgba(255,255,255,0.9);
        border-color: #d8d8d8;
    }}

    .brand-card h3,
    .brand-card p {{
        margin-top: 0;
    }}

    .brand-card p:last-child {{
        margin-bottom: 0;
    }}

    .brand-badges {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: var(--space-xs);
    }}

    .brand-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 999px;
        border: 1px solid var(--brand-hairline);
        background: rgba(255,255,255,0.05);
        color: var(--brand-ink);
        font-size: 11px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }}

    .brand-callout {{
        margin: var(--space-xs) 0;
        padding: 16px 18px;
        border-left: 3px solid var(--brand-primary);
        background: rgba(255,255,255,0.04);
        color: var(--brand-ink);
        line-height: 1.7;
    }}

    .brand-callout--success {{ border-left-color: var(--brand-success); }}
    .brand-callout--warning {{ border-left-color: #ffb347; }}
    .brand-callout--error {{ border-left-color: var(--brand-warning); }}
    .brand-callout--info {{ border-left-color: var(--brand-info); }}

    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button {{
        background: var(--brand-primary);
        color: var(--brand-ink);
        border: 1px solid var(--brand-primary);
        border-radius: 0 !important;
        min-height: 48px;
        padding: 0 28px;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-weight: 700;
    }}

    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {{
        background: var(--brand-primary-hover);
        border-color: var(--brand-primary-hover);
        color: var(--brand-ink);
    }}

    div[data-testid="stButton"] > button[kind="secondary"] {{
        background: transparent;
        border-color: rgba(255,255,255,0.38);
    }}

    div[data-testid="stFileUploader"],
    div[data-testid="stTextInputRootElement"],
    div[data-testid="stTextAreaRootElement"],
    div[data-baseweb="select"],
    div[data-testid="stNumberInputRootElement"] {{
        border-radius: 0 !important;
    }}

    div[data-baseweb="select"] > div,
    div[data-testid="stTextInputRootElement"] > div,
    div[data-testid="stTextAreaRootElement"] > div,
    div[data-testid="stFileUploader"] section {{
        background: rgba(24,24,24,0.82) !important;
        border: 1px solid var(--brand-hairline) !important;
    }}

    div[data-testid="stFileUploader"] small,
    div[data-testid="stTextInputRootElement"] input,
    div[data-testid="stTextAreaRootElement"] textarea {{
        color: var(--brand-ink) !important;
    }}

    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"],
    div[data-testid="stJson"] {{
        border: 1px solid var(--brand-hairline);
        background: rgba(24,24,24,0.72);
        padding: 6px;
    }}

    div[data-testid="stExpander"] details {{
        border: 1px solid var(--brand-hairline);
        background: rgba(48,48,48,0.5);
    }}

    div[data-testid="stExpander"] summary {{
        padding: 12px 16px;
        color: var(--brand-ink);
    }}

    button[data-baseweb="tab"] {{
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 12px;
        color: var(--brand-muted);
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--brand-ink);
    }}

    [data-testid="stNotification"] {{
        border-radius: 0 !important;
        border: 1px solid var(--brand-hairline);
    }}

    .brand-divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent);
        margin: var(--space-lg) 0;
    }}

    @media (max-width: 900px) {{
        .brand-hero {{
            margin-left: -1rem;
            margin-right: -1rem;
            padding: 88px 1rem 56px;
            min-height: 48vh;
        }}

        .brand-strip {{
            grid-template-columns: 1fr;
            margin-top: -18px;
        }}
    }}
</style>
"""


def apply_theme(page_title: str):
    st.set_page_config(page_title=page_title, layout="wide")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_hero(eyebrow: str, title: str, description: str):
    st.markdown(
        f"""
        <section class="brand-hero">
            <div class="brand-hero__content">
                <span class="brand-eyebrow">{eyebrow}</span>
                <h1>{title}</h1>
                <p>{description}</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_metric_strip(items: list[tuple[str, str]]):
    body = "".join(
        f'<div class="brand-metric"><span class="brand-metric__label">{label}</span><span class="brand-metric__value">{value}</span></div>'
        for label, value in items
    )
    st.markdown(f'<section class="brand-strip">{body}</section>', unsafe_allow_html=True)


def render_section_intro(eyebrow: str, title: str, description: str = "", light: bool = False):
    extra = " brand-section--light" if light else ""
    description_html = f'<p class="brand-section__desc">{description}</p>' if description else ""
    st.markdown(
        f"""
        <section class="brand-section{extra}">
            <p class="brand-section__eyebrow">{eyebrow}</p>
            <h2 class="brand-section__title">{title}</h2>
            {description_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_card(title: str, body: str, eyebrow: str | None = None, light: bool = False):
    extra = " brand-card--light" if light else ""
    eyebrow_html = f'<p class="brand-section__eyebrow">{eyebrow}</p>' if eyebrow else ""
    st.markdown(
        f"""
        <div class="brand-card{extra}">
            {eyebrow_html}
            <h3>{title}</h3>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_badges(labels: list[str]):
    body = "".join(f'<span class="brand-badge">{label}</span>' for label in labels)
    st.markdown(f'<div class="brand-badges">{body}</div>', unsafe_allow_html=True)


def render_callout(content: str, tone: str = "info"):
    st.markdown(f'<div class="brand-callout brand-callout--{tone}">{content}</div>', unsafe_allow_html=True)


def render_divider():
    st.markdown('<div class="brand-divider"></div>', unsafe_allow_html=True)
