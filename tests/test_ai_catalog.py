"""AI 提供商与模型目录测试。"""

import pytest

from models import (
    CatalogError,
    create_model,
    create_provider,
    delete_model,
    delete_provider,
    ensure_ai_catalog_tables,
    get_catalog,
    get_provider,
    update_model,
    update_provider,
    update_user_ai_config,
)


PUBLIC_BASE_URL = 'https://8.8.8.8/v1'


def _create_provider(**overrides):
    payload = {
        'slug': 'moonshot',
        'name': 'Moonshot',
        'description': 'Moonshot 兼容接口',
        'driver': 'openai_compatible',
        'base_url': PUBLIC_BASE_URL,
        'currency': 'CNY',
        'enabled': True,
        'allow_custom_model': False,
        'requires_base_url': False,
        'sort_order': 50,
    }
    payload.update(overrides)
    return create_provider(payload)


def _create_model(provider_id, **overrides):
    payload = {
        'provider_id': provider_id,
        'model_id': 'moonshot-v1-8k',
        'display_name': 'Moonshot 8K',
        'input_price': 0.001,
        'output_price': 0.002,
        'enabled': True,
        'is_default': True,
        'sort_order': 10,
    }
    payload.update(overrides)
    return create_model(payload)


class TestCatalogStorage:
    def test_seed_catalog_contains_builtin_providers(self, temp_db):
        ensure_ai_catalog_tables()
        catalog = get_catalog()
        slugs = {provider['slug'] for provider in catalog}

        assert {'dashscope', 'deepseek', 'custom'} <= slugs
        dashscope = next(p for p in catalog if p['slug'] == 'dashscope')
        assert dashscope['is_builtin'] is True
        assert dashscope['default_model']
        assert dashscope['model_details']

    def test_create_update_delete_provider_and_model(self, temp_db):
        provider_id = _create_provider()
        provider = get_provider('moonshot')
        assert provider is not None
        assert provider['name'] == 'Moonshot'

        model_pk = _create_model(provider_id)
        assert get_provider('moonshot')['default_model'] == 'moonshot-v1-8k'

        update_model(model_pk, {'input_price': 0.003, 'display_name': 'Moonshot 8K v2'})
        assert get_provider('moonshot')['model_details'][0]['input_price'] == 0.003

        update_provider(provider_id, {'name': 'Moonshot AI', 'enabled': False})
        assert get_provider('moonshot')['name'] == 'Moonshot AI'
        assert get_provider('moonshot')['enabled'] is False

        delete_model(model_pk)
        delete_provider(provider_id)
        assert get_provider('moonshot') is None

    def test_slug_and_model_id_are_immutable(self, temp_db):
        provider_id = _create_provider()
        model_pk = _create_model(provider_id)

        update_provider(provider_id, {'slug': 'other', 'name': 'Moonshot'})
        update_model(model_pk, {
            'model_id': 'other-model',
            'provider_id': 999,
            'display_name': 'Moonshot 8K',
        })

        provider = get_provider('moonshot')
        assert provider['slug'] == 'moonshot'
        assert provider['model_details'][0]['model_id'] == 'moonshot-v1-8k'

    def test_duplicate_slug_and_model_rejected(self, temp_db):
        provider_id = _create_provider()
        with pytest.raises(CatalogError) as exc:
            _create_provider()
        assert exc.value.status == 409

        _create_model(provider_id)
        with pytest.raises(CatalogError) as exc:
            _create_model(provider_id)
        assert exc.value.status == 409

    def test_default_model_is_unique(self, temp_db):
        provider_id = _create_provider()
        first = _create_model(provider_id, model_id='model-a', is_default=True)
        second = _create_model(provider_id, model_id='model-b', is_default=True)

        models = {m['model_id']: m for m in get_provider('moonshot')['model_details']}
        assert models['model-a']['is_default'] is False
        assert models['model-b']['is_default'] is True

        update_model(first, {'is_default': True})
        models = {m['model_id']: m for m in get_provider('moonshot')['model_details']}
        assert models['model-a']['is_default'] is True
        assert models['model-b']['is_default'] is False

    def test_default_model_promoted_after_delete(self, temp_db):
        provider_id = _create_provider()
        first = _create_model(provider_id, model_id='model-a', is_default=True)
        _create_model(provider_id, model_id='model-b', is_default=False)

        delete_model(first)

        provider = get_provider('moonshot')
        assert provider['default_model'] == 'model-b'

    def test_last_enabled_model_cannot_be_disabled(self, temp_db):
        provider_id = _create_provider()
        model_pk = _create_model(provider_id)

        with pytest.raises(CatalogError) as exc:
            update_model(model_pk, {'enabled': False})
        assert '至少需要保留一个启用模型' in str(exc.value)

        with pytest.raises(CatalogError) as exc:
            delete_model(model_pk)
        assert '至少需要保留一个启用模型' in str(exc.value)

    def test_custom_model_provider_can_remove_all_models(self, temp_db):
        provider_id = _create_provider(
            slug='openrouter', base_url='https://8.8.8.4/v1', allow_custom_model=True)
        model_pk = _create_model(provider_id)

        update_model(model_pk, {'enabled': False})
        delete_model(model_pk)
        assert get_provider('openrouter')['model_details'] == []

    def test_builtin_provider_cannot_be_deleted(self, temp_db):
        ensure_ai_catalog_tables()
        provider = get_provider('dashscope')

        with pytest.raises(CatalogError) as exc:
            delete_provider(provider['provider_pk'])
        assert '内置供应商不可删除' in str(exc.value)

    def test_referenced_provider_and_model_cannot_be_deleted(self, temp_db, test_admin_user):
        provider_id = _create_provider()
        model_pk = _create_model(provider_id)
        update_user_ai_config(
            test_admin_user['id'],
            {'ai_provider': 'moonshot', 'ai_model': 'moonshot-v1-8k'},
        )

        with pytest.raises(CatalogError) as exc:
            delete_model(model_pk)
        assert exc.value.status == 409

        with pytest.raises(CatalogError) as exc:
            delete_provider(provider_id)
        assert exc.value.status == 409

    def test_invalid_base_url_rejected(self, temp_db):
        with pytest.raises(CatalogError):
            _create_provider(base_url='http://127.0.0.1:8080/v1')

    def test_prices_validation(self, temp_db):
        provider_id = _create_provider()
        with pytest.raises(CatalogError):
            _create_model(provider_id, input_price=-1)

    def test_tag_generator_uses_catalog_model_and_pricing(self, temp_db):
        from ai_services import TagGenerator

        provider_id = _create_provider()
        _create_model(provider_id, input_price=0.001, output_price=0.002)

        provider = TagGenerator.create_provider('moonshot', 'sk-test', model=None)

        assert provider.model == 'moonshot-v1-8k'
        assert provider.BASE_URL == PUBLIC_BASE_URL.rstrip('/')
        assert provider.COST_PER_1K_TOKENS['moonshot-v1-8k'] == {
            'input': 0.001,
            'output': 0.002,
        }
        assert provider.CURRENCY == 'CNY'


class TestCatalogRoutes:
    def _login(self, client, user):
        client.post('/login', data={
            'username': user['username'],
            'password': user['password'],
        })

    def test_catalog_page_requires_admin(self, client, test_admin_user, test_user):
        self._login(client, test_admin_user)
        response = client.get('/admin/ai/catalog')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'AI 提供商与模型管理' in html
        assert '新增供应商' in html
        assert '新增模型' in html
        assert 'providerDialog' in html

        client.get('/logout')
        self._login(client, test_user)
        response = client.get('/admin/ai/catalog')
        assert response.status_code in (302, 403)

    def test_admin_can_create_provider_and_model_via_api(
            self, client, test_admin_user):
        self._login(client, test_admin_user)
        response = client.post('/admin/ai/catalog/providers', json={
            'slug': 'moonshot',
            'name': 'Moonshot',
            'driver': 'openai_compatible',
            'base_url': PUBLIC_BASE_URL,
            'currency': 'CNY',
            'enabled': True,
        })
        assert response.status_code == 200
        provider_id = response.get_json()['id']

        response = client.post('/admin/ai/catalog/models', json={
            'provider_id': provider_id,
            'model_id': 'moonshot-v1-8k',
            'input_price': 0.001,
            'output_price': 0.002,
            'enabled': True,
        })
        assert response.status_code == 200

        catalog = client.get('/admin/ai/catalog/data').get_json()['data']
        provider = next(p for p in catalog if p['slug'] == 'moonshot')
        assert provider['default_model'] == 'moonshot-v1-8k'

    def test_api_returns_conflict_for_duplicate_slug(self, client, test_admin_user):
        self._login(client, test_admin_user)
        payload = {
            'slug': 'moonshot',
            'name': 'Moonshot',
            'driver': 'openai_compatible',
            'base_url': PUBLIC_BASE_URL,
            'currency': 'CNY',
        }
        assert client.post('/admin/ai/catalog/providers', json=payload).status_code == 200
        response = client.post('/admin/ai/catalog/providers', json=payload)
        assert response.status_code == 409
        assert response.get_json()['success'] is False

    def test_admin_can_update_and_delete_catalog_via_api(
            self, client, test_admin_user):
        self._login(client, test_admin_user)
        provider_id = client.post('/admin/ai/catalog/providers', json={
            'slug': 'moonshot',
            'name': 'Moonshot',
            'driver': 'openai_compatible',
            'base_url': PUBLIC_BASE_URL,
            'currency': 'CNY',
        }).get_json()['id']
        model_pk = client.post('/admin/ai/catalog/models', json={
            'provider_id': provider_id,
            'model_id': 'moonshot-v1-8k',
        }).get_json()['id']

        response = client.put(f'/admin/ai/catalog/providers/{provider_id}', json={
            'name': 'Moonshot AI',
            'enabled': False,
        })
        assert response.status_code == 200

        response = client.put(f'/admin/ai/catalog/models/{model_pk}', json={
            'input_price': 0.005,
            'output_price': 0.006,
        })
        assert response.status_code == 200

        assert client.delete(f'/admin/ai/catalog/models/{model_pk}').status_code == 200
        assert client.delete(f'/admin/ai/catalog/providers/{provider_id}').status_code == 200

        catalog = client.get('/admin/ai/catalog/data').get_json()['data']
        assert not any(provider['slug'] == 'moonshot' for provider in catalog)

    def test_non_admin_cannot_modify_catalog(self, client, test_user):
        self._login(client, test_user)
        response = client.post('/admin/ai/catalog/providers', json={
            'slug': 'moonshot',
            'name': 'Moonshot',
            'driver': 'openai_compatible',
            'base_url': PUBLIC_BASE_URL,
            'currency': 'CNY',
        })
        assert response.status_code in (302, 403)

    def test_ai_settings_page_links_to_catalog(self, client, test_admin_user):
        self._login(client, test_admin_user)
        html = client.get('/admin/ai/configure').get_data(as_text=True)
        assert '管理提供商与模型' in html
        assert '/admin/ai/catalog' in html

    def test_configure_rejects_unknown_provider(self, client, test_admin_user):
        self._login(client, test_admin_user)
        response = client.post('/admin/ai/configure', json={
            'ai_provider': 'not-exists',
            'ai_model': 'x',
            'ai_api_key': 'sk-test',
        })
        assert response.status_code == 400
        assert '不支持的AI提供商' in response.get_json()['error']

    def test_configure_fills_default_model(self, client, test_admin_user):
        self._login(client, test_admin_user)
        response = client.post('/admin/ai/configure', json={
            'ai_provider': 'deepseek',
            'ai_model': '',
            'ai_api_key': 'sk-test',
        })
        assert response.status_code == 200

        from models import get_user_ai_config
        config = get_user_ai_config(test_admin_user['id'])
        assert config['ai_provider'] == 'deepseek'
        assert config['ai_model']
