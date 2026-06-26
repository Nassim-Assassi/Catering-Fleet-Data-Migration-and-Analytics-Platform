import paths


class TestPathsConstants:
    def test_repo_dir_points_to_pipeline_directory(self):
        assert paths.REPO_DIR.name == "pipeline"

    def test_extracted_and_transformed_file_names_are_stable(self):
        assert paths.EXTRACTED_TRUCK_DATA_FILE.name == "extracted_truck_data.csv"
        assert paths.EXTRACTED_PAYMENT_METHOD_DATA_FILE.name == "extracted_payment_method_data.csv"
        assert paths.EXTRACTED_TRANSACTION_DATA_FILE.name == "extracted_transaction_data.csv"
        assert paths.TRANSFORMED_TRUCK_DATA_FILE.name == "transformed_truck_data.csv"
        assert paths.TRANSFORMED_PAYMENT_METHOD_DATA_FILE.name == "transformed_payment_method_data.csv"
        assert paths.TRANSFORMED_TRANSACTION_DATA_FILE.name == "transformed_transaction_data.csv"
