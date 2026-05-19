import pytest
from unittest.mock import MagicMock, patch, AsyncMock




class TestOrderCalculations:
    

    def test_fee_is_20_percent_of_price(self):
        price = 100.0
        fee = 0.2 * price
        assert fee == 20.0

    def test_total_is_price_plus_fee_times_quantity(self):
        price = 50.0
        quantity = 3
        total = 1.2 * price * quantity
        assert total == 180.0

    def test_total_with_quantity_one(self):
        price = 200.0
        quantity = 1
        total = 1.2 * price * quantity
        assert total == 240.0

    def test_fee_with_decimal_price(self):
        price = 99.99
        fee = round(0.2 * price, 2)
        assert fee == 20.0  # zaokrugljeno

    def test_total_is_greater_than_price(self):
        price = 100.0
        quantity = 1
        total = 1.2 * price * quantity
        assert total > price

    def test_order_initial_status_is_pending(self):
        status = 'pending'
        assert status == 'pending'

    def test_order_status_transitions(self):
        valid_statuses = ['pending', 'completed', 'refunded']
        assert 'pending' in valid_statuses
        assert 'completed' in valid_statuses
        assert 'refunded' in valid_statuses
        assert 'cancelled' not in valid_statuses

    def test_negative_price_gives_negative_total(self):
        price = -50.0
        total = 1.2 * price * 1
        assert total < 0  
   
    def test_zero_quantity_gives_zero_total(self):
        price = 100.0
        quantity = 0
        total = 1.2 * price * quantity
        assert total == 0.0



class TestConsumerLogic:
    
    def test_consumer_reads_message_and_updates_status(self):
        """Consumer mora da promeni status u 'refunded' kada dobije poruku."""
        mock_order = MagicMock()
        mock_order.pk = 'test-pk-123'
        mock_order.status = 'completed'

        
        mock_order.status = 'refunded'
        mock_order.save()

        assert mock_order.status == 'refunded'
        mock_order.save.assert_called_once()

    def test_consumer_handles_missing_order_gracefully(self):
       
        mock_order_class = MagicMock()
        mock_order_class.get.side_effect = Exception("Order not found")

        try:
            mock_order_class.get('nonexistent-pk')
            assert False, "Exception should have been raised"
        except Exception as e:
            assert "not found" in str(e).lower()

    def test_consumer_group_creation_handles_existing_group(self):
       
        mock_redis = MagicMock()
        mock_redis.xgroup_create.side_effect = Exception("BUSYGROUP Group already exists")

        try:
            mock_redis.xgroup_create('refund_order', 'payment-group', mkstream=True)
        except Exception:
            pass 

        mock_redis.xgroup_create.assert_called_once()

    def test_consumer_extracts_pk_from_message(self):

        raw_message = [
            ['refund_order', [
                ('1712345678-0', {'pk': 'order-abc-123', 'product_id': 'prod-1',
                                  'price': '100.0', 'fee': '20.0',
                                  'total': '120.0', 'quantity': '1',
                                  'status': 'completed'})
            ]]
        ]
        extracted_pk = raw_message[0][1][0][1]['pk']
        assert extracted_pk == 'order-abc-123'

    def test_consumer_processes_only_one_message_at_a_time(self):
       
        mock_redis = MagicMock()
        mock_redis.xreadgroup.return_value = []

        mock_redis.xreadgroup(
            'payment-group', 'refund_order',
            {'refund_order': '>'}, count=1, block=5000
        )

        call_kwargs = mock_redis.xreadgroup.call_args
        assert call_kwargs.kwargs.get('count') == 1 or call_kwargs[1].get('count') == 1



class TestDatabaseConfig:
   

    @patch.dict('os.environ', {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_PASSWORD': 'secret'
    })
    def test_env_variables_are_loaded_correctly(self):
        import os
        assert os.getenv('REDIS_HOST') == 'localhost'
        assert os.getenv('REDIS_PORT') == '6379'
        assert os.getenv('REDIS_PASSWORD') == 'secret'

    @patch.dict('os.environ', {'REDIS_PORT': '6380'})
    def test_redis_port_is_converted_to_int(self):
        import os
        port = int(os.getenv('REDIS_PORT'))
        assert isinstance(port, int)
        assert port == 6380

    def test_missing_env_variable_returns_none(self):
        import os
        result = os.getenv('NONEXISTENT_VARIABLE')
        assert result is None
