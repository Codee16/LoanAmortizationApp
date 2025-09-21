import streamlit as st
import numpy_financial as npf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ------------------ PAGE CONFIG ------------------ #
st.set_page_config(page_title="Mortgage Calculator", layout="wide")
st.title("🏡 Mortgage & Financial Analytics")

# ------------------ DISCLAIMER ------------------ #
with st.expander("⚠️ Disclaimer"):
    st.write("""
    This app is for **educational purposes only** and should not be considered financial advice.  
    Calculations are based on user inputs and assumptions.  
    Please consult with a qualified financial advisor before making decisions.
    """)

# ------------------ TABS ------------------ #
tab1, tab2, tab3 = st.tabs([
    "🏠 Mortgage Calculator", 
    "📈 Property Value & Net Proceeds", 
    "💰 Rent vs Buy Analytics"
])

# ------------------ TAB 1: Mortgage Calculator ------------------ #
with tab1:
    st.header("Mortgage Calculator")

    with st.form("mortgage_form"):
        col1, col2 = st.columns(2)

        with col1:
            property_value = st.number_input("Property Value ($)", value=575000, step=1000)
            downpayment_pct = st.number_input("Down Payment (%)", value=20.0, step=1.0)
            loan_start_date = st.date_input("Loan Start Date", value=datetime.today())
            tenure_years = st.number_input("Loan Tenure (Years)", min_value=1, value=30, step=1)
            payments_per_year = st.number_input("Payments per Year", min_value=1, value=12, step=1)
            one_time_payment = st.number_input("One-time Lump Sum Payment ($)", min_value=0.0, value=0.0, step=1000.0)
            one_time_payment_date = st.date_input("One-time Payment Date", value=datetime.today())
            tax_rebate = st.number_input("Lump Sum Tax Rebate ($)", min_value=0.0, value=0.0, step=1000.0)

        with col2:
            true_rate = st.number_input("True Loan Rate (%)", min_value=0.1, value=4.99, step=0.01)
            interest_rate_1 = st.number_input("Customer Rate Year 1 (%)", min_value=0.1, value=2.99, step=0.01)
            interest_rate_2 = st.number_input("Customer Rate Year 2 (%)", min_value=0.1, value=3.99, step=0.01)
            property_tax_rate = st.number_input("Annual Property Tax Rate (%)", min_value=0.0, value=2.85, step=0.01)
            hoa_fee = st.number_input("Monthly HOA Fee ($)", min_value=0.0, value=66.0, step=10.0)
            insurance = st.number_input("Monthly Property Insurance ($)", min_value=0.0, value=150.0, step=10.0)
            addl_regular_payment = st.number_input("Additional Regular Payment ($)", min_value=0.0, value=0.0, step=100.0)

        submitted = st.form_submit_button("Calculate Schedule")

    if submitted:
        loan_amount = property_value * (1 - downpayment_pct / 100)
        num_payments = tenure_years * payments_per_year
        rate_per_period_true = (true_rate / 100) / payments_per_year
        base_payment = npf.pmt(rate_per_period_true, num_payments, -loan_amount)

        balance = loan_amount
        schedule = []
        current_date = loan_start_date

        # Effective property value for tax calculation (rebate applied)
        effective_property_value = property_value - tax_rebate

        for n in range(1, num_payments + 1):
            current_year = (n - 1) // payments_per_year + 1

            # Interest and principal split
            true_interest = balance * rate_per_period_true
            principal_payment = base_payment - true_interest + addl_regular_payment

            # Subsidized customer interest
            if current_year == 1:
                customer_rate = (interest_rate_1 / 100) / payments_per_year
            elif current_year == 2:
                customer_rate = (interest_rate_2 / 100) / payments_per_year
            else:
                customer_rate = rate_per_period_true
            customer_interest = balance * customer_rate

            # One-time lump sum
            if one_time_payment > 0 and current_date == one_time_payment_date:
                principal_payment += one_time_payment

            if principal_payment > balance:
                principal_payment = balance
            balance -= principal_payment

            # Property tax based on effective property value
            property_tax = (property_tax_rate / 100) * effective_property_value / payments_per_year
            total_payment = customer_interest + principal_payment + hoa_fee + insurance + property_tax

            schedule.append([
                current_date, balance, principal_payment, customer_interest,
                true_interest, total_payment, hoa_fee, property_tax, insurance
            ])

            if balance <= 0:
                break

            current_date += timedelta(days=365 // payments_per_year)

        df = pd.DataFrame(schedule, columns=[
            "Date", "Balance", "Principal", "CustomerInterest",
            "TrueInterest", "TotalPayment", "HOA", "PropertyTax", "Insurance"
        ])
        df["Year"] = pd.to_datetime(df["Date"]).dt.year
        df["Principal+Interest"] = df["Principal"] + df["CustomerInterest"]

        st.success("✅ Amortization schedule generated")
        st.dataframe(df.head(24))

        # Visualization
        st.plotly_chart(
            px.area(df, x="Date", y=["Principal", "CustomerInterest"], 
                    title="Principal vs Interest Over Time"), 
            use_container_width=True
        )
        st.session_state["df"] = df
        st.session_state["loan_params"] = {
            "property_value": property_value,
            "tenure_years": tenure_years,
            "selling_cost_pct": 8.0
        }

# ------------------ TAB 2: Property Value & Net Proceeds ------------------ #
with tab2:
    st.header("Property Value & Net Proceeds Analysis")

    if "df" in st.session_state:
        df = st.session_state["df"]
        property_value = st.session_state["loan_params"]["property_value"]
        tenure_years = st.session_state["loan_params"]["tenure_years"]

        property_growth = st.number_input("Annual Property Growth (%)", value=2.5, step=0.1)
        age_threshold = st.number_input("Growth Slows After (Years)", value=10, step=1)
        depreciation_factor = st.number_input("Annual Growth Reduction After Threshold (%)", value=0.2, step=0.1)
        selling_cost_pct = st.number_input("Selling Cost (%)", min_value=0.0, value=8.0, step=0.1)

        # ---------------- Property Value Growth vs Selling Cost (with age impact) ---------------- #
        prop_values = [property_value]
        years = tenure_years
        for i in range(1, years + 1):
            effective_growth = property_growth
            if i > age_threshold:
                effective_growth -= depreciation_factor * (i - age_threshold)
            effective_growth = max(effective_growth, -100)  # prevent extreme negative growth
            prop_values.append(prop_values[-1] * (1 + effective_growth / 100))

        selling_cost_rate = selling_cost_pct / 100
        net_proceeds = [v - v * selling_cost_rate for v in prop_values]

        # Bubble size scaled
        bubble_sizes = [max(10, min(50, (v - min(net_proceeds)) / (max(net_proceeds) - min(net_proceeds) + 1e-5) * 40 + 10)) for v in net_proceeds]
        # Bubble color
        bubble_colors = ["red" if v < property_value else "green" for v in net_proceeds]

        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=list(range(0, years + 1)),
            y=prop_values,
            mode='lines+markers',
            name="Property Value",
            line=dict(color="blue")
        ))
        fig4.add_trace(go.Scatter(
            x=list(range(0, years + 1)),
            y=net_proceeds,
            mode='markers',
            name=f"Net Proceeds (after {selling_cost_pct}% selling cost)",
            marker=dict(size=bubble_sizes, color=bubble_colors, sizemode='area',
                        sizeref=2.*max(bubble_sizes)/(50.**2), line=dict(width=1, color='black')),
            text=[f"${v:,.0f}" for v in net_proceeds],
            hoverinfo="text+y+x"
        ))
        fig4.update_layout(title=f"Property Value Growth vs Selling Cost (Net Proceeds as Bubbles)",
                           xaxis_title="Year", yaxis_title="Value ($)", showlegend=True)
        st.plotly_chart(fig4, use_container_width=True)

        # ---------------- Net Proceed Table ---------------- #
        df["Year"] = pd.to_datetime(df["Date"]).dt.year
        yearly_balance = df.groupby("Year")["Balance"].last().reset_index()
        net_proceed_table = pd.DataFrame({
            "Year": list(range(df["Year"].min(), df["Year"].min() + years + 1)),
            "PropertyValue": prop_values,
            "NetProceedsAfterSellingCost": net_proceeds
        })
        net_proceed_table = net_proceed_table.merge(yearly_balance, how="left", left_on="Year", right_on="Year")
        net_proceed_table["ActualNetProceed"] = net_proceed_table["NetProceedsAfterSellingCost"] - net_proceed_table["Balance"].fillna(0)

        # ✅ Add Net Gain/Loss column (vs Original Purchase Price)
        original_property_value = st.session_state["loan_params"]["property_value"]
        net_proceed_table["NetGainOrLoss"] = net_proceed_table["NetProceedsAfterSellingCost"] - original_property_value

        st.subheader("Net Proceed Table (Net Proceeds - Remaining Loan Balance)")
        def highlight_gain_loss(val):
            color = 'green' if val >= 0 else 'red'
            return f'color: {color}; font-weight: bold;'

        st.dataframe(
            net_proceed_table.style.applymap(highlight_gain_loss, subset=["NetGainOrLoss"]).format({
                "PropertyValue": "${:,.0f}",
                "NetProceedsAfterSellingCost": "${:,.0f}",
                "Balance": "${:,.0f}",
                "ActualNetProceed": "${:,.0f}",
                "NetGainOrLoss": "${:,.0f}"
            })
        )

# ------------------ TAB 3: Rent vs Buy ------------------ #
with tab3:
    st.header("Rent vs Buy Analytics")

    if "df" in st.session_state:
        df = st.session_state["df"]

        col1, col2 = st.columns(2)
        with col1:
            rent = st.number_input("Monthly Rent ($)", min_value=0, value=1500, step=100)
        with col2:
            rent_increase = st.number_input("Annual Rent Increase (%)", min_value=0.0, value=3.0, step=0.5)

        df_yearly = df.groupby("Year").agg({
            "CustomerInterest": "sum",
            "HOA": "sum",
            "PropertyTax": "sum",
            "Insurance": "sum",
            "Principal": "sum"
        }).reset_index()

        base_rent = rent
        rent_growth_rate = rent_increase / 100
        df_yearly["AnnualRent"] = [base_rent * ((1 + rent_growth_rate) ** i) * 12 for i in range(len(df_yearly))]
        df_yearly["TotalNonEquityCost"] = df_yearly["CustomerInterest"] + df_yearly["HOA"] + df_yearly["PropertyTax"] + df_yearly["Insurance"]
        df_yearly["EquityBuilt"] = df_yearly["Principal"].cumsum()

        st.subheader("📉 Yearly Rent vs Mortgage Costs")
        st.dataframe(df_yearly)

        st.plotly_chart(
            px.bar(df_yearly, x="Year", y=["TotalNonEquityCost", "AnnualRent"], 
                   barmode="group", title="Rent vs Mortgage Non-Equity Payments"),
            use_container_width=True
        )
        st.plotly_chart(
            px.line(df_yearly, x="Year", y="EquityBuilt", title="Equity Built Over Time"),
            use_container_width=True
        )
# ------------------ Footer / Developer Info ------------------ #
st.markdown("---")
st.markdown(
    "<p style='text-align: center; font-size:14px;'>Developed by <b>Alok Kumar Mishra</b></p>",
    unsafe_allow_html=True
)
