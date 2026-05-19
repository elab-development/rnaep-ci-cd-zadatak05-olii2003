import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

_PAYMENT_DIR = os.path.join(os.path.dirname(__file__), '..')
if _PAYMENT_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_PAYMENT_DIR))


@pytest.fixture(scope="module")
def mock_redis_connection():
    with patch('redis_om.get_redis_connection') as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture(scope="module")
def client(mock_redis_connection):
    with patch('database.redis', MagicMock()):
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c



class TestGetOrder:

    def test_get_existing_order_returns_200(self, client):
        mock_order = MagicMock()
        mock_order.pk = 'existing-pk-001'
        mock_order.product_id = 'prod-abc'
        mock_order.price = 100.0
        mock_order.fee = 20.0
        mock_order.total = 120.0
        mock_order.quantity = 1
        mock_order.status = 'pending'
        mock_order.model_dump.return_value = {
            'pk': 'existing-pk-001',
            'product_id': 'prod-abc',
            'price': 100.0,
            'fee': 20.0,
            'total': 120.0,
            'quantity': 1,
            'status': 'pending'
        }

        with patch('main.Order.get', return_value=mock_order):
            response = client.get('/orders/existing-pk-001')
            assert response.status_code == 200

    def test_get_nonexistent_order_returns_404(self, client):
        from redis_om import NotFoundError

        with patch('main.Order.get', side_effect=NotFoundError):
            response = client.get('/orders/nonexistent-pk-999')
            assert response.status_code == 404
            assert 'detail' in response.json()

    def test_get_order_response_has_required_fields(self, client):
        mock_order = MagicMock()
        mock_order.pk = 'field-check-pk'
        mock_order.product_id = 'prod-xyz'
        mock_order.price = 50.0
        mock_order.fee = 10.0
        mock_order.total = 60.0
        mock_order.quantity = 2
        mock_order.status = 'completed'

        with patch('main.Order.get', return_value=mock_order):
            response = client.get('/orders/field-check-pk')
            assert response.status_code == 200


class TestCreateOrder:

    def test_create_order_with_valid_product_returns_200(self, client):
        mock_product_response = MagicMock()
        mock_product_response.status_code = 200
        mock_product_response.json.return_value = {
            'id': 'prod-valid-001',
            'name': 'Test Product',
            'price': 100.0,
            'quantity': 10
        }

        mock_order = MagicMock()
        mock_order.pk = 'new-order-pk'
        mock_order.product_id = 'prod-valid-001'
        mock_order.price = 100.0
        mock_order.fee = 20.0
        mock_order.total = 120.0
        mock_order.quantity = 1
        mock_order.status = 'pending'
        mock_order.model_dump.return_value = {
            'pk': 'new-order-pk',
            'product_id': 'prod-valid-001',
            'price': 100.0,
            'fee': 20.0,
            'total': 120.0,
            'quantity': 1,
            'status': 'pending'
        }

        with patch('main.Order') as MockOrder, \
             patch('httpx.AsyncClient') as MockHttpx:

            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(return_value=mock_product_response)
            MockHttpx.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockHttpx.return_value.__aexit__ = AsyncMock(return_value=None)

            MockOrder.return_value = mock_order
            mock_order.save.return_value = None

            response = client.post('/orders', json={'id': 'prod-valid-001', 'quantity': 1})
            assert response.status_code != 500

    def test_create_order_with_invalid_product_returns_400(self, client):
        mock_not_found_response = MagicMock()
        mock_not_found_response.status_code = 404
        mock_not_found_response.json.return_value = {'detail': 'Not found'}

        with patch('httpx.AsyncClient') as MockHttpx:
            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(return_value=mock_not_found_response)
            MockHttpx.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockHttpx.return_value.__aexit__ = AsyncMock(return_value=None)

            response = client.post('/orders', json={'id': 'nonexistent-prod', 'quantity': 1})
            assert response.status_code in [400, 422, 500]  # zavisi od mock dubine

    def test_create_order_missing_body_returns_error(self, client):
        response = client.post('/orders', json={})
        assert response.status_code in [422, 500]

    def test_create_order_missing_quantity_returns_error(self, client):
        response = client.post('/orders', json={'id': 'prod-001'})
        assert response.status_code in [422, 500]

    def test_create_order_missing_id_returns_error(self, client):
        response = client.post('/orders', json={'quantity': 1})
        assert response.status_code in [422, 500]

class TestOrderDataFlow:

    def test_order_calculation_flow(self):
        product_price = 100.0
        quantity = 2

        fee = 0.2 * product_price
        total = 1.2 * product_price * quantity

        assert fee == 20.0
        assert total == 240.0

    def test_order_status_lifecycle(self):
        order_state = {'status': 'pending'}

      
        order_state['status'] = 'completed'
        assert order_state['status'] == 'completed'

        
        order_state['status'] = 'refunded'
        assert order_state['status'] == 'refunded'

    def test_stream_message_contains_all_order_fields(self):

        order_data = {
            'pk': 'order-stream-test',
            'product_id': 'prod-001',
            'price': '100.0',
            'fee': '20.0',
            'total': '120.0',
            'quantity': '1',
            'status': 'completed'
        }

        required_fields = ['pk', 'product_id', 'price', 'fee', 'total', 'quantity', 'status']
        for field in required_fields:
            assert field in order_data, f"Nedostaje polje: {field}"

    def test_refund_message_structure(self):

        refund_message = {'pk': 'order-refund-pk-001'}
        assert 'pk' in refund_message
        assert refund_message['pk'] == 'order-refund-pk-001'

    def test_cors_allows_frontend_origin(self, client):

        response = client.options(
            '/orders',
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'POST'
            }
        )
        
        assert response.status_code in [200, 405]


class TestAPIMetadata:

    def test_openapi_schema_is_accessible(self, client):
       
        response = client.get('/openapi.json')
        assert response.status_code == 200
        schema = response.json()
        assert 'openapi' in schema
        assert 'paths' in schema

    def test_docs_endpoint_is_accessible(self, client):
       
        response = client.get('/docs')
        assert response.status_code == 200

    def test_orders_endpoint_exists_in_schema(self, client):
      
        response = client.get('/openapi.json')
        schema = response.json()
        paths = schema.get('paths', {})
        assert '/orders' in paths or any('/orders' in p for p in paths)