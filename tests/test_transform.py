import pandas as pd
import transform


class TestValidateFields:
    def test_validate_fields_returns_false_on_missing_columns(self):
        df = pd.DataFrame({"truck_id": [1]})
        expected = {"truck_id": "int", "truck_name": "str"}

        result = transform.validate_fields(df, expected, "DIM_Truck")

        assert result is False


class TestFilterInvalidTruckRows:
    def test_filter_invalid_truck_rows_removes_out_of_range_values(self):
        df = pd.DataFrame(
            {
                "truck_id": [1, 2, 3],
                "truck_name": ["A", "B", "C"],
                "truck_description": ["x", "y", "z"],
                "has_card_reader": [1, 3, 0],
                "fsa_rating": [5, 4, 9],
            }
        )

        result = transform.filter_invalid_truck_rows(df)

        assert len(result) == 1
        assert result.iloc[0]["truck_id"] == 1


class TestAddYMdColumns:
    def test_add_y_m_d_columns_adds_date_parts(self):
        df = pd.DataFrame({"at": ["2026-06-15 13:45:00"]})

        result = transform.add_y_m_d_columns(df.copy(), date_column="at")

        assert result.loc[0, "year"] == 2026
        assert result.loc[0, "month"] == 6
        assert result.loc[0, "day"] == 15


class TestTransformPaymentMethodData:
    def test_transform_payment_method_data_normalizes_and_filters_values(self):
        df = pd.DataFrame(
            {
                "payment_method_id": [1, 2, 3],
                "payment_method": [" Card ", "CASH", "bank"],
            }
        )

        result = transform.transform_payment_method_data(df)

        assert result["payment_method"].tolist() == ["card", "cash"]
