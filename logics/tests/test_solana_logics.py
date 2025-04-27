import pytest
import datetime
from unittest import TestCase
from unittest.mock import patch, MagicMock
from logics.solana_logics import get_first_transaction_for_program
from logics.solana_logics import get_program_first_deployment_time_by_helius
from logics.solana_logics import get_program_first_deployment_time_by_rpc
from logics.solana_logics import get_program_first_deployment_timestamp


class TestGetFirstDeploymentTimeByHelius(TestCase):
    @patch("logics.solana_logics.requests.post")
    def test_successful_response(self, mock_post):
        mock_response = MagicMock()
        first_tx_time = 1714099300
        mock_response.json.return_value = {
            "result": [
                {"blockTime": 1714099200},
                {"blockTime": first_tx_time}
            ]
        }
        mock_post.return_value = mock_response
        timestamp = get_program_first_deployment_time_by_helius("dummy_program_id", is_mainnet=False)
        assert timestamp == first_tx_time

    @patch("logics.solana_logics.requests.post")
    def test_no_transactions(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_post.return_value = mock_response

        timestamp = get_program_first_deployment_time_by_helius("dummy_program_id", is_mainnet=False)
        assert timestamp is None

    @patch("logics.solana_logics.requests.post")
    def test_request_failure(self, mock_post):
        mock_post.side_effect = Exception("Network error")

        timestamp = get_program_first_deployment_time_by_helius("dummy_program_id", is_mainnet=False)
        assert timestamp is None

    @patch("logics.solana_logics.requests.post")
    def test_invalid_json_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("Invalid JSON")
        mock_post.return_value = mock_response

        timestamp = get_program_first_deployment_time_by_helius("dummy_program_id", is_mainnet=False)
        assert timestamp is None


class TestGetFirstTransactionForProgram(TestCase):
    @patch("logics.solana_logics.requests.post")
    def test_successful_response(self, mock_post):
        mock_response = MagicMock()
        first_tx_time = 1714099300
        first_tx_hash = "efgh5678"
        mock_response.json.return_value = {
            "result": [
                {"blockTime": 1714099200, "signature": "abcd1234"},
                {"blockTime": first_tx_time, "signature": first_tx_hash}
            ]
        }
        mock_post.return_value = mock_response

        timestamp, signature = get_first_transaction_for_program("dummy_program_id", is_mainnet=False)
        assert timestamp == first_tx_time
        assert signature == first_tx_hash

    @patch("logics.solana_logics.requests.post")
    def test_no_transactions(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_post.return_value = mock_response

        timestamp, signature = get_first_transaction_for_program("dummy_program_id", is_mainnet=False)
        assert timestamp == 0
        assert signature == ""

    @patch("logics.solana_logics.requests.post")
    def test_request_failure(self, mock_post):
        mock_post.side_effect = Exception("Network error")

        timestamp, signature = get_first_transaction_for_program("dummy_program_id", is_mainnet=False)
        assert timestamp is None
        assert signature is None

    @patch("logics.solana_logics.requests.post")
    def test_invalid_json_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("Invalid JSON")
        mock_post.return_value = mock_response

        timestamp, signature = get_first_transaction_for_program("dummy_program_id", is_mainnet=False)
        assert timestamp is None
        assert signature is None

    @patch("logics.solana_logics.requests.post")
    def test_before_transaction_and_limit(self, mock_post):
        mock_response = MagicMock()
        first_tx_time = 1714099400
        first_tx_hash = "abcd123"
        mock_response.json.return_value = {
            "result": [
                {"blockTime": first_tx_time, "signature": first_tx_hash}
            ]
        }
        mock_post.return_value = mock_response

        timestamp, signature = get_first_transaction_for_program(
            "dummy_program_id",
            before_transaction="dummy_before_tx",
            limit=10,
            is_mainnet=False
        )
        assert timestamp == first_tx_time
        assert signature == first_tx_hash


class TestGetProgramFirstDeploymentTimeByRPC(TestCase):
    @patch("logics.solana_logics.get_first_transaction_for_program")
    @patch("logics.solana_logics.check_is_first_deploy_tx_in_rpc_call")
    def test_multi_page_find(self, mock_check, mock_get_first_tx):
        first_tx_timestamp = 1234566000
        first_tx_hash = "tx0"
        mock_get_first_tx.return_value = (first_tx_timestamp, first_tx_hash)
        mock_check.return_value = True

        timestamp = get_program_first_deployment_time_by_rpc("dummy_program_id", is_mainnet=False)

        assert timestamp == first_tx_timestamp
        assert mock_get_first_tx.call_count == 2
        assert mock_check.call_count == 1

    @patch("logics.solana_logics.get_first_transaction_for_program")
    def test_no_transactions(self, mock_get_first_tx):
        mock_get_first_tx.return_value = (None, None)

        timestamp = get_program_first_deployment_time_by_rpc("dummy_program_id")

        assert timestamp is None
        mock_get_first_tx.assert_called_once()

    @patch("logics.solana_logics.get_first_transaction_for_program")
    @patch("logics.solana_logics.check_is_first_deploy_tx_in_rpc_call")
    def test_intermediate_rpc_failure(self, mock_check, mock_get_first_tx):
        # Simulate exception thrown during 2nd call
        mock_get_first_tx.side_effect = [
            (1234567890, "tx1"),
            Exception("RPC Error")
        ]
        mock_check.return_value = False

        with pytest.raises(Exception):
            get_program_first_deployment_time_by_rpc("dummy_program_id")


class TestGetProgramFirstDeploymentTimestamp(TestCase):
    @patch('logics.solana_logics.cache')
    @patch('logics.solana_logics.get_utc_timestamp')
    def test_get_from_cache(self, mock_get_utc_timestamp, mock_cache):
        mock_cache.get.return_value = b'1234567890'
        mock_get_utc_timestamp.return_value = datetime.datetime(2023, 1, 1)

        result = get_program_first_deployment_timestamp('test_program')
        self.assertEqual(result, (1234567890, datetime.datetime(2023, 1, 1)))
        mock_cache.get.assert_called_once()

    @patch('logics.solana_logics.cache')
    @patch('logics.solana_logics.random.choice')
    @patch('logics.solana_logics.get_utc_timestamp')
    def test_get_from_rpc_success(self, mock_get_utc_timestamp, mock_random_choice, mock_cache):
        mock_cache.get.return_value = None
        mock_func = MagicMock(return_value=1234567890)
        mock_random_choice.return_value = mock_func
        mock_get_utc_timestamp.return_value = datetime.datetime(2023, 1, 1)

        result = get_program_first_deployment_timestamp('test_program')
        self.assertEqual(result, (1234567890, datetime.datetime(2023, 1, 1)))
        mock_func.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch('logics.solana_logics.cache')
    @patch('logics.solana_logics.random.choice')
    def test_rpc_failure(self, mock_random_choice, mock_cache):
        mock_cache.get.return_value = None
        mock_func = MagicMock(side_effect=Exception("RPC failure"))
        mock_random_choice.return_value = mock_func

        unix_timestamp, _ = get_program_first_deployment_timestamp('test_program')
        self.assertIsNone(unix_timestamp)
        mock_func.assert_called_once()

    @patch('logics.solana_logics.cache')
    @patch('logics.solana_logics.random.choice')
    def test_invalid_timestamp(self, mock_random_choice, mock_cache):
        mock_cache.get.return_value = None
        mock_func = MagicMock(return_value=None)
        mock_random_choice.return_value = mock_func

        unix_timestamp, _ = get_program_first_deployment_timestamp('test_program')
        self.assertIsNone(unix_timestamp)
        mock_func.assert_called_once()
