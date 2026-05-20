import pytest
import os
from unittest.mock import patch

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)


@pytest.fixture(scope="module")
def real_redis():
    from redis_om import get_redis_connection
    r = get_redis_connection(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    yield r
    for key in r.keys("payment-integration-test:*"):
        r.delete(key)


@pytest.fixture(scope="module")
def order_model(real_redis):
    from redis_om import HashModel

    class Order(HashModel, index=True):
        product_id: str
        price: float
        fee: float
        total: float
        quantity: int
        status: str

        class Meta:
            database = real_redis

    return Order


class TestOrderCRUD:

    def test_create_order_persists_to_redis(self, order_model):
        order = order_model(
            product_id='prod-001',
            price=100.0,
            fee=20.0,
            total=120.0,
            quantity=1,
            status='pending'
        )
        order.save()

        assert order.pk is not None
        retrieved = order_model.get(order.pk)
        assert retrieved.product_id == 'prod-001'
        assert retrieved.status == 'pending'

    def test_update_order_status_to_completed(self, order_model):
        order = order_model(
            product_id='prod-002',
            price=50.0,
            fee=10.0,
            total=60.0,
            quantity=2,
            status='pending'
        )
        order.save()
        order.status = 'completed'
        order.save()

        refreshed = order_model.get(order.pk)
        assert refreshed.status == 'completed'

    def test_update_order_status_to_refunded(self, order_model):
        order = order_model(
            product_id='prod-003',
            price=75.0,
            fee=15.0,
            total=90.0,
            quantity=1,
            status='completed'
        )
        order.save()
        order.status = 'refunded'
        order.save()

        refreshed = order_model.get(order.pk)
        assert refreshed.status == 'refunded'

    def test_get_nonexistent_order_raises_error(self, order_model):
        from redis_om import NotFoundError
        with pytest.raises(NotFoundError):
            order_model.get('nonexistent-pk-xyz')

    def test_order_fields_have_correct_types(self, order_model):
        order = order_model(
            product_id='prod-types-test',
            price=99.99,
            fee=19.998,
            total=119.988,
            quantity=3,
            status='pending'
        )
        order.save()

        retrieved = order_model.get(order.pk)
        assert isinstance(retrieved.price, float)
        assert isinstance(retrieved.quantity, int)
        assert isinstance(retrieved.status, str)


class TestRedisStreamIntegration:

    def test_xadd_writes_message_to_stream(self, real_redis):
        stream_key = 'integration-test-stream'
        msg_id = real_redis.xadd(stream_key, {'pk': 'order-123', 'status': 'completed'})
        assert msg_id is not None
        real_redis.delete(stream_key)

    def test_xgroup_create_creates_consumer_group(self, real_redis):
        stream_key = 'integration-test-group-stream'
        group_name = 'integration-test-group'
        real_redis.xadd(stream_key, {'init': 'true'})
        real_redis.xgroup_create(stream_key, group_name, id='0')
        real_redis.delete(stream_key)

    def test_xgroup_create_existing_group_raises_error(self, real_redis):
        stream_key = 'integration-test-duplicate-group'
        group_name = 'duplicate-group'
        real_redis.xadd(stream_key, {'init': 'true'})
        real_redis.xgroup_create(stream_key, group_name, id='0')
        with pytest.raises(Exception):
            real_redis.xgroup_create(stream_key, group_name, id='0')
        real_redis.delete(stream_key)

    def test_xreadgroup_reads_pending_messages(self, real_redis):
        stream_key = 'integration-test-read-stream'
        group_name = 'read-test-group'
        consumer_name = 'test-consumer'
        real_redis.xadd(stream_key, {'pk': 'order-readtest-001'})
        real_redis.xgroup_create(stream_key, group_name, id='0')
        results = real_redis.xreadgroup(
            group_name, consumer_name,
            {stream_key: '>'}, count=1
        )
        assert len(results) > 0
        message_data = results[0][1][0][1]
        assert message_data['pk'] == 'order-readtest-001'
        real_redis.delete(stream_key)

    def test_refund_order_stream_flow(self, real_redis, order_model):
        stream_key = 'refund-integration-test'
        group_name = 'refund-int-group'

        order = order_model(
            product_id='prod-refund-int',
            price=100.0,
            fee=20.0,
            total=120.0,
            quantity=1,
            status='completed'
        )
        order.save()

        real_redis.xadd(stream_key, {'pk': order.pk})
        real_redis.xgroup_create(stream_key, group_name, id='0')

        results = real_redis.xreadgroup(
            group_name, 'test-consumer',
            {stream_key: '>'}, count=1
        )

        assert results
        message_data = results[0][1][0][1]
        fetched_order = order_model.get(message_data['pk'])
        fetched_order.status = 'refunded'
        fetched_order.save()

        final_order = order_model.get(order.pk)
        assert final_order.status == 'refunded'

        real_redis.delete(stream_key)