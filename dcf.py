"""Five-year FCFF DCF. All dollar inputs are USD millions."""

# Editable inputs
STARTING_FCFF = 100
GROWTH_RATES = [0.08, 0.06, 0.05, 0.04, 0.03]
WACC = 0.10
TERMINAL_GROWTH = 0.03
NON_OPERATING_CASH = 50
DEBT = 300
DILUTED_SHARES = 50  # Millions of shares

# Editable sensitivity and reverse-DCF settings (rates are decimal fractions)
SENSITIVITY_WACCS = [0.09, 0.10, 0.11]
SENSITIVITY_TERMINAL_GROWTHS = [0.02, 0.03, 0.04]
TARGET_SHARE_PRICE = 30.00  # USD per diluted share
REVERSE_SHIFT_LOWER = -0.05  # -5 percentage points
REVERSE_SHIFT_UPPER = 0.10  # +10 percentage points


# LLY inputs: USD millions, shares in millions. Forecasts are analyst assumptions.
# Carried from the existing Lab 4 operating forecast, converted from billions.
# FCFF = revenue * EBIT margin * (1-tax) + D&A - capex - change in NWC.
# 2026: revenue=86000, EBIT margin=46%, tax=18.5%, D&A=2.5%, capex=13%,
# change in NWC=20% * (86000-65179), giving normalized FCFF=19047.2.
# 2027-31 revenue growth: 25%,20%,15%,10%,7%; EBIT margins: 46%,47%,48%,48%,47%;
# D&A/revenue: 2.5%,3%,3.5%,4%,4%; capex/revenue: 12%,11%,10%,9%,8%;
# tax=18.5% and NWC=20% of incremental revenue. These imply FCFF of
# 25789.25, 34793.45, 44521.77, 52711.722, 57614.6672475.
LLY_STARTING_FCFF = 19047.2  # Normalized 2026 forecast, not reported cash flow
LLY_GROWTH_RATES = [0.3539654122390696, 0.3491454772822009,
                    0.2796020515355620, 0.1839538724538581, 0.0930143251153888]
LLY_WACC = 0.09  # Analyst assumption, not an observed cost of capital
LLY_TERMINAL_GROWTH = 0.03  # Analyst assumption
LLY_NON_OPERATING_CASH = 8950 + 60 + 3856  # Cash + short/noncurrent investments
LLY_DEBT = 7050 + 47858  # June 30, 2026 book debt
LLY_DILUTED_SHARES = 894  # 2026 guidance proxy, not a spot diluted count
LLY_TARGET_SHARE_PRICE = 1123.00  # Captured quote; edit to update, no live fetch
LLY_PRICE_TIMESTAMP = "2026-09-10 20:51:06 UTC"
LLY_PRICE_SOURCE = "Web finance quote for NYSE:LLY (captured September 10, 2026)"
LLY_FINANCIAL_SOURCE = "https://www.sec.gov/Archives/edgar/data/59478/000005947826000081/lly-20260630.htm"
LLY_GUIDANCE_SOURCE = "https://investor.lilly.com/news-releases/news-release-details/lilly-reports-second-quarter-2026-financial-results-raises-full"

# Both cases share the editable sensitivity lists and reverse-shift bounds above.
TRAINING_INPUTS = (STARTING_FCFF, GROWTH_RATES, WACC, TERMINAL_GROWTH,
                   NON_OPERATING_CASH, DEBT, DILUTED_SHARES)
LLY_INPUTS = (LLY_STARTING_FCFF, LLY_GROWTH_RATES, LLY_WACC, LLY_TERMINAL_GROWTH,
             LLY_NON_OPERATING_CASH, LLY_DEBT, LLY_DILUTED_SHARES)


def share_value(wacc, terminal_growth, growth_shift=0.0, inputs=TRAINING_INPUTS):
    """Value with all original inputs fixed except the three arguments."""
    (STARTING_FCFF, GROWTH_RATES, WACC, TERMINAL_GROWTH,
     NON_OPERATING_CASH, DEBT, DILUTED_SHARES) = inputs
    if terminal_growth >= wacc:
        raise ValueError("terminal growth must be less than WACC")
    fcff = STARTING_FCFF
    explicit_pv = 0.0
    for year, growth in enumerate(GROWTH_RATES, start=1):
        fcff *= 1 + growth + growth_shift
        explicit_pv += fcff / (1 + wacc) ** year
    terminal_value = fcff * (1 + terminal_growth) / (wacc - terminal_growth)
    enterprise_value = explicit_pv + terminal_value / (1 + wacc) ** len(GROWTH_RATES)
    return (enterprise_value + NON_OPERATING_CASH - DEBT) / DILUTED_SHARES


def print_sensitivity(inputs=TRAINING_INPUTS):
    print("\nSensitivity: value per diluted share (USD)")
    headers = ["WACC / terminal growth"] + [
        f"{growth:.2%}" for growth in SENSITIVITY_TERMINAL_GROWTHS
    ]
    rows = []
    for wacc in SENSITIVITY_WACCS:
        rows.append([f"{wacc:.2%}"] + [
            "INVALID" if growth >= wacc else f"{share_value(wacc, growth, inputs=inputs):.4f}"
            for growth in SENSITIVITY_TERMINAL_GROWTHS
        ])
    widths = [max(len(row[i]) for row in [headers] + rows)
              for i in range(len(headers))]
    def format_row(row):
        return " | ".join(cell.rjust(width) for cell, width in zip(row, widths))
    print(format_row(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(format_row(row))
    print("INVALID means terminal growth is greater than or equal to WACC.")


def solve_growth_shift(inputs=TRAINING_INPUTS, target=TARGET_SHARE_PRICE):
    """Bisect a valid bracket; return None when it does not bracket the target."""
    from math import isfinite

    (STARTING_FCFF, GROWTH_RATES, WACC, TERMINAL_GROWTH,
     NON_OPERATING_CASH, DEBT, DILUTED_SHARES) = inputs
    TARGET_SHARE_PRICE = target

    lower, upper = REVERSE_SHIFT_LOWER, REVERSE_SHIFT_UPPER
    if not all(isfinite(value) for value in (lower, upper, TARGET_SHARE_PRICE)):
        raise ValueError("bounds and target price must be finite")
    if lower >= upper:
        raise ValueError("lower shift bound must be less than upper shift bound")
    if any(1 + growth + bound <= 0
           for growth in GROWTH_RATES for bound in (lower, upper)):
        raise ValueError("bracket pushes an annual growth rate to -100% or below")

    def residual(shift):
        result = share_value(WACC, TERMINAL_GROWTH, shift, inputs) - TARGET_SHARE_PRICE
        if not isfinite(result):
            raise ValueError("valuation must be finite throughout the bracket")
        return result

    lower_error, upper_error = residual(lower), residual(upper)
    if lower_error == 0:
        return lower
    if upper_error == 0:
        return upper
    if (lower_error > 0) == (upper_error > 0):
        return None
    for _ in range(200):
        midpoint = (lower + upper) / 2
        midpoint_error = residual(midpoint)
        if abs(midpoint_error) <= 1e-10:
            return midpoint
        if midpoint == lower or midpoint == upper:
            break
        if (midpoint_error > 0) == (lower_error > 0):
            lower, lower_error = midpoint, midpoint_error
        else:
            upper = midpoint
    raise ValueError("bisection did not converge to the target price")


def print_reverse_dcf(inputs=TRAINING_INPUTS, target=TARGET_SHARE_PRICE):
    (STARTING_FCFF, GROWTH_RATES, WACC, TERMINAL_GROWTH,
     NON_OPERATING_CASH, DEBT, DILUTED_SHARES) = inputs
    TARGET_SHARE_PRICE = target
    print("\nReverse DCF: uniform shift added to all five explicit growth rates")
    print(f"Target share price (USD): {TARGET_SHARE_PRICE:.4f}")
    print(f"Shift bracket (percentage points): "
          f"[{100 * REVERSE_SHIFT_LOWER:+.6f}, {100 * REVERSE_SHIFT_UPPER:+.6f}]")
    print(f"Inputs held fixed: STARTING_FCFF={STARTING_FCFF}; "
          f"base GROWTH_RATES={GROWTH_RATES} (only the uniform shift varies); "
          f"WACC={WACC}; TERMINAL_GROWTH={TERMINAL_GROWTH}; "
          f"NON_OPERATING_CASH={NON_OPERATING_CASH}; DEBT={DEBT}; "
          f"DILUTED_SHARES={DILUTED_SHARES}; forecast length={len(GROWTH_RATES)} years")
    try:
        shift = solve_growth_shift(inputs, target)
    except ValueError as error:
        print(f"Reverse DCF refused: {error}.")
        return
    if shift is None:
        print("No solution in that bracket.")
        return
    print(f"Solved uniform growth shift (percentage points): {100 * shift:+.8f}")
    print(f"Value per diluted share at solved shift (USD): "
          f"{share_value(WACC, TERMINAL_GROWTH, shift, inputs):.4f}")


def main(inputs=TRAINING_INPUTS, target=TARGET_SHARE_PRICE):
    (STARTING_FCFF, GROWTH_RATES, WACC, TERMINAL_GROWTH,
     NON_OPERATING_CASH, DEBT, DILUTED_SHARES) = inputs

    if TERMINAL_GROWTH >= WACC:
        raise SystemExit("Error: terminal growth must be less than WACC.")
    if len(GROWTH_RATES) != 5:
        raise SystemExit("Error: provide exactly five yearly growth rates.")

    fcff = STARTING_FCFF
    yearly_fcff = []
    for growth in GROWTH_RATES:
        fcff *= 1 + growth
        yearly_fcff.append(fcff)

    explicit_pv = sum(
        cash_flow / (1 + WACC) ** year
        for year, cash_flow in enumerate(yearly_fcff, start=1)
    )
    terminal_value = yearly_fcff[-1] * (1 + TERMINAL_GROWTH) / (WACC - TERMINAL_GROWTH)
    terminal_pv = terminal_value / (1 + WACC) ** len(GROWTH_RATES)
    enterprise_value = explicit_pv + terminal_pv
    equity_value = enterprise_value + NON_OPERATING_CASH - DEBT
    value_per_share = equity_value / DILUTED_SHARES
    terminal_share = terminal_pv / enterprise_value

    for year, cash_flow in enumerate(yearly_fcff, start=1):
        print(f"FCFF Year {year} (USD millions): {cash_flow:.4f}")
    print(f"PV of five explicit FCFF (USD millions): {explicit_pv:.4f}")
    print(f"Terminal value at Year 5 (USD millions): {terminal_value:.4f}")
    print(f"PV of terminal value (USD millions): {terminal_pv:.4f}")
    print(f"Enterprise value (USD millions): {enterprise_value:.4f}")
    print(f"Equity value (USD millions): {equity_value:.4f}")
    print(f"Value per diluted share (USD): {value_per_share:.4f}")
    print(f"PV of terminal value / enterprise value (fraction): {terminal_share:.4f}")

    print_sensitivity(inputs)
    print_reverse_dcf(inputs, target)


def print_lilly_call():
    print("\nEli Lilly conditional call")
    print("Watch-defer. Initiate if the growth implied by Lilly's share price "
          "is supported by Mounjaro and Zepbound sales growth after accounting "
          "for pricing pressure and manufacturing investment; otherwise, defer.")
    print("Monitor: next quarter's combined Mounjaro and Zepbound revenue growth.")


if __name__ == "__main__":
    print(f"TRAINING CASE - not an Eli Lilly valuation; target USD {TARGET_SHARE_PRICE:.2f}")
    main()
    print("\nELI LILLY (NYSE: LLY) - simplified five-year FCFF DCF")
    print(f"Target quote: USD {LLY_TARGET_SHARE_PRICE:.2f}; {LLY_PRICE_TIMESTAMP}")
    print(f"Price source: {LLY_PRICE_SOURCE}; frozen snapshot, not auto-updated.")
    print("Forecasts: normalized 2026 FCFF anchor; 2027-2031 FCFF growth from Lab 4.")
    print("Timing: five annual periods from valuation; no 2026 stub or terminal ROIC adjustment.")
    print("This simplified lab model therefore differs from the Lab 4 valuation.")
    print("Assumptions: normalized FCFF excludes separate acquisition/IPR&D cash outlays;")
    print("all listed financial assets are treated as nonoperating at book value;")
    print("894 million shares is a guidance proxy. WACC and growth are assumptions.")
    print("Reverse variable: FCFF growth shift, not revenue or EPS growth;")
    print("operating assumptions inform the base path but are not recomputed by the shift.")
    print(f"Financial source: {LLY_FINANCIAL_SOURCE}")
    print(f"Guidance source: {LLY_GUIDANCE_SOURCE}")
    main(LLY_INPUTS, LLY_TARGET_SHARE_PRICE)
    print_lilly_call()
