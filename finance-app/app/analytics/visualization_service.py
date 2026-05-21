from __future__ import annotations

import pandas as pd


class VisualizationService:
    def __init__(self, frame: pd.DataFrame):
        self.frame = frame.copy()
        if not self.frame.empty:
            self.frame["transaction_date"] = pd.to_datetime(self.frame["transaction_date"])

    def plotly_line_income_expense(self) -> dict:
        monthly = self._monthly_frame()
        return {
            "data": [
                {
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Income",
                    "x": monthly["period"].tolist(),
                    "y": monthly["income"].round(2).tolist(),
                },
                {
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Expenses",
                    "x": monthly["period"].tolist(),
                    "y": monthly["expenses"].round(2).tolist(),
                },
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Net",
                    "x": monthly["period"].tolist(),
                    "y": monthly["net"].round(2).tolist(),
                },
            ],
            "layout": {"title": "Monthly Income vs Expenses", "xaxis": {"title": "Month"}, "yaxis": {"title": "Amount"}},
        }

    def plotly_pie_expenses_by_category(self) -> dict:
        expense = self.frame[self.frame["type"] == "expense"]
        grouped = expense.groupby("category_name", dropna=False)["amount"].sum().sort_values(ascending=False)
        return {
            "data": [
                {
                    "type": "pie",
                    "labels": grouped.index.fillna("Uncategorized").tolist(),
                    "values": grouped.round(2).tolist(),
                    "hole": 0.35,
                }
            ],
            "layout": {"title": "Expense Composition by Category"},
        }

    def plotly_bar_monthly_expenses(self) -> dict:
        monthly = self._monthly_frame()
        return {
            "data": [
                {
                    "type": "bar",
                    "name": "Expenses",
                    "x": monthly["period"].tolist(),
                    "y": monthly["expenses"].round(2).tolist(),
                }
            ],
            "layout": {"title": "Monthly Expense Bar Chart", "xaxis": {"title": "Month"}, "yaxis": {"title": "Expenses"}},
        }

    def plotly_scatter_transactions(self) -> dict:
        return {
            "data": [
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": self.frame["transaction_date"].dt.strftime("%Y-%m-%d").tolist() if not self.frame.empty else [],
                    "y": self.frame["amount"].round(2).tolist() if not self.frame.empty else [],
                    "marker": {
                        "size": 9,
                        "color": ["#1f77b4" if item == "income" else "#d62728" for item in self.frame.get("type", pd.Series([], dtype=str))],
                    },
                    "text": self.frame.get("category_name", pd.Series([], dtype=str)).fillna("Uncategorized").tolist(),
                }
            ],
            "layout": {"title": "Transaction Scatter", "xaxis": {"title": "Date"}, "yaxis": {"title": "Amount"}},
        }

    def plotly_box_expenses(self) -> dict:
        expense_values = self.frame.loc[self.frame["type"] == "expense", "amount"].round(2).tolist() if not self.frame.empty else []
        return {
            "data": [{"type": "box", "name": "Expenses", "y": expense_values}],
            "layout": {"title": "Expense Boxplot"},
        }

    def plotly_histogram_amounts(self) -> dict:
        return {
            "data": [{"type": "histogram", "x": self.frame["amount"].round(2).tolist() if not self.frame.empty else [], "nbinsx": 20}],
            "layout": {"title": "Transaction Amount Distribution"},
        }

    def plotly_heatmap_weekday_month(self) -> dict:
        if self.frame.empty:
            z = []
            months = []
        else:
            work = self.frame.copy()
            work["month"] = work["transaction_date"].dt.month
            work["weekday"] = work["transaction_date"].dt.day_name().str.slice(0, 3)
            matrix = (
                work[work["type"] == "expense"]
                .pivot_table(index="weekday", columns="month", values="amount", aggfunc="mean", fill_value=0)
                .reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], fill_value=0)
            )
            z = matrix.round(2).values.tolist()
            months = [str(int(m)) for m in matrix.columns.tolist()]
        return {
            "data": [{"type": "heatmap", "x": months, "y": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "z": z}],
            "layout": {"title": "Average Expense Heatmap by Weekday and Month"},
        }

    def plotly_treemap_category(self) -> dict:
        grouped = self.frame.groupby("category_name", dropna=False)["amount"].sum().sort_values(ascending=False)
        labels = grouped.index.fillna("Uncategorized").tolist()
        return {
            "data": [{"type": "treemap", "labels": labels, "parents": [""] * len(labels), "values": grouped.round(2).tolist()}],
            "layout": {"title": "Transaction Treemap by Category"},
        }

    def plotly_radar_top_categories(self) -> dict:
        grouped = (
            self.frame[self.frame["type"] == "expense"]
            .groupby("category_name", dropna=False)["amount"]
            .sum()
            .sort_values(ascending=False)
            .head(6)
        )
        labels = grouped.index.fillna("Uncategorized").tolist()
        values = grouped.round(2).tolist()
        return {
            "data": [{"type": "scatterpolar", "r": values, "theta": labels, "fill": "toself", "name": "Top Expense Categories"}],
            "layout": {"title": "Expense Radar", "polar": {"radialaxis": {"visible": True}}},
        }

    def plotly_moving_average(self, window: int = 3) -> dict:
        monthly = self._monthly_frame()
        moving = monthly["expenses"].rolling(window=window, min_periods=1).mean()
        return {
            "data": [
                {"type": "scatter", "mode": "lines+markers", "name": "Expenses", "x": monthly["period"].tolist(), "y": monthly["expenses"].round(2).tolist()},
                {"type": "scatter", "mode": "lines", "name": f"{window}-Period MA", "x": monthly["period"].tolist(), "y": moving.round(2).tolist()},
            ],
            "layout": {"title": "Expense Moving Average"},
        }

    def plotly_rolling_statistics(self, window: int = 3) -> dict:
        monthly = self._monthly_frame()
        rolling_mean = monthly["expenses"].rolling(window=window, min_periods=1).mean()
        rolling_std = monthly["expenses"].rolling(window=window, min_periods=1).std().fillna(0)
        upper = rolling_mean + rolling_std
        lower = (rolling_mean - rolling_std).clip(lower=0)
        return {
            "data": [
                {"type": "scatter", "mode": "lines", "name": "Rolling Mean", "x": monthly["period"].tolist(), "y": rolling_mean.round(2).tolist()},
                {"type": "scatter", "mode": "lines", "name": "Upper Band", "x": monthly["period"].tolist(), "y": upper.round(2).tolist()},
                {"type": "scatter", "mode": "lines", "name": "Lower Band", "x": monthly["period"].tolist(), "y": lower.round(2).tolist()},
            ],
            "layout": {"title": "Rolling Statistics (Mean +/- Std)"},
        }

    def _monthly_frame(self) -> pd.DataFrame:
        if self.frame.empty:
            return pd.DataFrame(columns=["period", "income", "expenses", "net"])
        grouped = (
            self.frame.assign(period=self.frame["transaction_date"].dt.to_period("M").astype(str))
            .groupby(["period", "type"], as_index=False)["amount"]
            .sum()
        )
        pivot = grouped.pivot(index="period", columns="type", values="amount").fillna(0).reset_index()
        if "income" not in pivot:
            pivot["income"] = 0.0
        if "expense" not in pivot:
            pivot["expense"] = 0.0
        pivot["net"] = pivot["income"] - pivot["expense"]
        pivot = pivot.rename(columns={"expense": "expenses"})
        return pivot.sort_values("period")
