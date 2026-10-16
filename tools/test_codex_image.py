"""Regression checks for Codex image requests and helper error reporting."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class CodexImageTests(unittest.TestCase):
    def test_image_alias_uses_codex_chat_executor(self):
        with patch.object(main, 'codex_env_value', return_value=''):
            for alias in ('', 'gpt-image-2', 'gpt-image-2.5-sunburst', 'gpt-image-2.5-flare', '$imagegen'):
                self.assertEqual(main.gpt_image_2_skill_model_arg(alias, 'codex'),
                                 'gpt-6.1-sol')

    def test_executor_override_and_explicit_model(self):
        with patch.object(main, 'codex_env_value', return_value='custom-executor'):
            self.assertEqual(main.gpt_image_2_skill_model_arg('gpt-image-2', 'codex'), 'custom-executor')
            self.assertEqual(main.gpt_image_2_skill_model_arg('explicit-executor', 'codex'), 'explicit-executor')

    def test_retired_executor_in_saved_requests_and_overrides_is_migrated(self):
        self.assertEqual(main.codex_model_for_exec('gpt-5.5'), 'gpt-6.1-sol')
        with patch.object(main, 'codex_env_value', return_value='gpt-5.5'):
            self.assertEqual(main.gpt_image_2_skill_model_arg('gpt-image-2', 'codex'), 'gpt-6.1-sol')
            self.assertEqual(main.gpt_image_2_skill_model_arg('gpt-5.5', 'codex'), 'gpt-6.1-sol')

    def test_saved_codex_models_are_migrated_without_changing_api_models(self):
        providers = main.merge_default_api_providers([
            {'id': 'codex', 'protocol': 'codex', 'chat_models': ['gpt-5.5', 'custom-executor', 'gpt-6.1-sol'], 'image_models': ['gpt-image-2.5-sunburst']},
            {'id': 'api', 'protocol': 'openai', 'chat_models': ['gpt-5.5'], 'image_models': ['gpt-image-2.5-sunburst']},
        ], inject_missing=False)
        self.assertEqual(providers[0]['chat_models'], ['gpt-6.1-sol', 'custom-executor'])
        self.assertEqual(providers[1]['chat_models'], ['gpt-5.5'])
        self.assertEqual(providers[0]['image_models'], ['gpt-image-2.5-sunburst'])
        self.assertEqual(providers[1]['image_models'], ['gpt-image-2.5-sunburst'])

    def test_openai_keeps_image_model(self):
        self.assertEqual(main.gpt_image_2_skill_model_arg('gpt-image-2', 'openai'), 'gpt-image-2')
        self.assertEqual(main.gpt_image_2_skill_model_arg('', 'openai'), main.OPENAI_DEFAULT_IMAGE_MODEL)

    def test_gpt_image_2_5_quality_levels(self):
        for model in ('gpt-image-2.5-sunburst', 'gpt-image-2.5-flare'):
            self.assertTrue(main.is_gpt_image_2_model(model))
            self.assertTrue(main.is_gpt_image_2_5_model(model))
            self.assertEqual(main.normalize_openai_image_quality(model, 'xhigh'), 'xhigh')
            self.assertEqual(main.normalize_openai_image_quality(model, 'max'), 'max')
        self.assertEqual(main.normalize_openai_image_quality('gpt-image-2', 'xhigh'), '')
        self.assertEqual(main.normalize_openai_image_quality('gpt-image-2', 'high'), 'high')

    def test_gpt_image_2_5_parameter_schema_exposes_new_quality_levels(self):
        fields = main.build_image_param_fields('api', {}, 'gpt-image-2.5-sunburst')
        quality = next(field for field in fields if field['key'] == 'quality')
        self.assertEqual([item['value'] for item in quality['options']],
                         ['auto', 'low', 'medium', 'high', 'xhigh', 'max'])

    def test_square_4k_keeps_square_composition_within_pixel_limit(self):
        size = main.gpt_image_2_skill_size_arg('4096x4096', provider='codex')
        width, height = main.parse_size_pair(size)
        self.assertEqual(width, height)
        self.assertGreater(width, 2048)
        self.assertLessEqual(width * height, main.GPT_IMAGE2_MAX_PIXELS)
        prompt = main.gpt_image_2_skill_prompt_arg('Product photo.', '4096x4096', 'codex')
        self.assertIn('4K', prompt)
        self.assertIn('aspect ratio 1:1', prompt)

    def test_portrait_and_landscape_are_not_swapped(self):
        self.assertEqual(main.gpt_image_2_skill_size_arg('2160x3840', provider='codex'), '2160x3840')
        self.assertEqual(main.gpt_image_2_skill_size_arg('3840x2160', provider='codex'), '3840x2160')
        self.assertEqual(main.gpt_image_2_skill_size_arg('1024x1024', provider='codex'), '1024x1024')

    def test_real_helper_http400_detail_is_visible(self):
        detail = "The 'gpt-5.5' model is not supported when using Codex with a ChatGPT account."
        output = json.dumps({'ok': False, 'error': {
            'code': 'http_error', 'message': 'HTTP 400',
            'detail': json.dumps({'detail': detail}),
        }}, indent=2)
        message = main.gpt_image_2_skill_failure_message(output, '', 1)
        self.assertIn('HTTP 400', message)
        self.assertIn(detail, message)

    def test_nested_api_error_and_progress_events(self):
        output = '\n'.join([
            json.dumps({'type': 'request.started', 'data': {'status': 'working'}}),
            json.dumps({'ok': False, 'error': {'message': 'HTTP 400', 'detail': json.dumps({
                'error': {'message': 'Invalid size parameter', 'code': 'invalid_value'}
            })}}),
        ])
        message = main.gpt_image_2_skill_failure_message(output, '', 1)
        self.assertIn('Invalid size parameter', message)
        self.assertNotIn('working', message)

    def test_plain_error_and_code_fallback(self):
        self.assertEqual(main.gpt_image_2_skill_failure_message('', 'connection refused', 1), 'connection refused')
        output = json.dumps({'ok': False, 'error': {'code': 'token_expired'}})
        self.assertEqual(main.gpt_image_2_skill_failure_message(output, '', 1), 'token_expired')


class CodexModelTests(unittest.IsolatedAsyncioTestCase):
    def test_sunburst_request_keeps_executor_and_image_model_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            reference = Path(folder) / 'reference.png'
            reference.write_bytes(b'reference image')
            with patch.object(main, 'codex_env_value', return_value=''):
                body = main.codex_image_request_body('Edit this image.', '1024x1024', 'gpt-image-2.5-sunburst', [str(reference)])
        self.assertEqual(body['model'], 'gpt-6.1-sol')
        self.assertEqual(body['tools'][0]['model'], 'gpt-image-2.5-sunburst')
        self.assertEqual(body['tools'][0]['action'], 'edit')
        self.assertEqual(body['tools'][0]['size'], '1024x1024')
        image_url = body['input'][0]['content'][1]['image_url']
        self.assertTrue(image_url.startswith('data:image/png;base64,'))
        self.assertEqual(main.base64.b64decode(image_url.split(',', 1)[1]), b'reference image')

    async def test_helper_receives_sunburst_and_never_silently_falls_back(self):
        request_files = []
        async def run_helper(args, **kwargs):
            self.assertIn('request', args)
            request_file = Path(args[args.index('--body-file') + 1])
            request_files.append(request_file)
            body = json.loads(request_file.read_text(encoding='utf-8'))
            self.assertEqual(body['model'], 'gpt-6.1-sol')
            self.assertEqual(body['tools'][0]['model'], 'gpt-image-2.5-sunburst')
            self.assertEqual(body['tools'][0]['action'], 'generate')
            return 1, b'{"ok": false, "error": {"message": "Unsupported image model"}}', b''
        run = AsyncMock(side_effect=run_helper)
        with patch.object(main, 'gpt_image_2_skill_executable', return_value='helper'), patch.object(main, 'gpt_image_2_skill_auth_file', return_value=''), patch.object(main, 'gpt_image_2_skill_provider_args', return_value=(['--provider', 'codex'], 'codex')), patch.object(main, 'gpt_image_2_skill_api_key', return_value=''), patch.object(main, 'codex_env_value', return_value=''), patch.object(main, 'run_captured_subprocess', run):
            with self.assertRaises(main.HTTPException) as error:
                await main.generate_codex_provider_image_via_gpt_image_2_skill('Draw a circle.', '1024x1024', 'gpt-image-2.5-sunburst')
        self.assertIn('Unsupported image model', error.exception.detail)
        self.assertEqual(run.await_count, 1)
        self.assertFalse(request_files[0].exists())

    async def test_api_model_discovery_recognizes_new_image_ids(self):
        def respond(request):
            self.assertEqual(str(request.url), 'https://api.openai.com/v1/models')
            self.assertEqual(request.headers['Authorization'], 'Bearer test-only-key')
            return main.httpx.Response(200, json={'data': [
                {'id': 'gpt-image-new-version'}, {'id': 'gpt-image-2.5-flare'}, {'id': 'gpt-6.1-sol'},
            ]})
        async_client = main.httpx.AsyncClient
        transport = main.httpx.MockTransport(respond)
        with patch.object(main.httpx, 'AsyncClient', side_effect=lambda *args, **kwargs: async_client(*args, transport=transport, **kwargs)):
            result = await main.fetch_models_from_upstream('https://api.openai.com/v1', 'test-only-key', 'openai')
        self.assertEqual(result['image_models'], ['gpt-image-2.5-flare', 'gpt-image-new-version'])
        self.assertEqual(result['chat_models'], ['gpt-6.1-sol'])
        self.assertIn('gpt-image-new-version', result['all'])

    def test_codex_image_preset_restores_sunburst_without_adding_flare(self):
        result = main.codex_models_payload({'models': [{'slug': 'upstream-a', 'visibility': 'list'}]})
        self.assertEqual(result['image_models'], ['gpt-image-2.5-sunburst'])
        self.assertEqual(result['model_sources']['gpt-image-2.5-sunburst'], '生图预设')
        self.assertNotIn('gpt-image-2', result['all'])
        self.assertNotIn('gpt-image-2.5-flare', result['all'])

    async def test_refresh_uses_cli_catalog_instead_of_project_defaults(self):
        catalog = {'models': [
            {'slug': 'upstream-a', 'display_name': 'Upstream A', 'visibility': 'list', 'base_instructions': 'private catalog text'},
            {'slug': 'hidden-model', 'visibility': 'hide'},
            {'slug': 'upstream-b', 'visibility': 'list'},
            {'slug': 'upstream-a', 'display_name': 'Upstream A', 'visibility': 'list'},
        ]}
        run = AsyncMock(return_value=(0, json.dumps(catalog).encode(), b''))
        with patch.object(main, 'codex_cli_executable', return_value='codex'), patch.object(main, 'run_captured_subprocess', run):
            result = await main.fetch_codex_models()
        self.assertEqual(run.call_args.args[0], ['codex', 'debug', 'models'])
        self.assertEqual(result['chat_models'], ['upstream-a', 'upstream-b'])
        self.assertEqual(result['model_names']['upstream-a'], 'Upstream A')
        self.assertEqual(result['model_sources']['upstream-b'], 'Codex 上游')
        self.assertEqual(result['image_models'], main.CODEX_DEFAULT_IMAGE_MODELS)
        self.assertNotIn('private catalog text', json.dumps(result))

    async def test_failed_refresh_never_returns_project_or_bundled_defaults(self):
        bundled = json.dumps({'models': [{'slug': 'bundled-model'}]}).encode()
        for response in [
            (1, b'', b'failed to refresh models'),
            (0, bundled, b'WARN failed to refresh available models; using bundled catalog'),
            (0, b'not json', b''),
            (0, b'{}', b''),
            (0, b'{"models": []}', b''),
        ]:
            with self.subTest(response=response):
                with patch.object(main, 'codex_cli_executable', return_value='codex'), patch.object(main, 'run_captured_subprocess', AsyncMock(return_value=response)):
                    with self.assertRaises(main.HTTPException) as error:
                        await main.fetch_codex_models()
                    self.assertEqual(error.exception.status_code, 502)

    async def test_refresh_timeout_is_reported(self):
        with patch.object(main, 'codex_cli_executable', return_value='codex'), patch.object(main, 'run_captured_subprocess', AsyncMock(side_effect=asyncio.TimeoutError)):
            with self.assertRaises(main.HTTPException) as error:
                await main.fetch_codex_models()
            self.assertEqual(error.exception.status_code, 504)

    async def test_fetch_and_verify_routes_share_the_live_catalog(self):
        expected = {'chat_models': ['upstream-a'], 'all': ['upstream-a']}
        fetch = AsyncMock(return_value=expected)
        payload = main.TestConnectionPayload(protocol='codex')
        with patch.object(main, 'fetch_codex_models', fetch), patch.object(main, 'get_api_provider_exact', return_value={'id': 'codex', 'protocol': 'codex'}):
            self.assertEqual(await main.fetch_upstream_models_from_payload(payload), expected)
            self.assertEqual(await main.fetch_upstream_models('codex'), expected)
            self.assertEqual(await main.test_provider_connection(payload), expected)
        self.assertEqual(fetch.await_count, 3)


if __name__ == '__main__':
    unittest.main()
