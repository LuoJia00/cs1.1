"""Regression checks for Codex image requests and helper error reporting."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class CodexImageTests(unittest.TestCase):
    def test_image_alias_uses_codex_chat_executor(self):
        with patch.object(main, 'codex_env_value', return_value=''):
            for alias in ('', 'gpt-image-2', 'gpt-image-2.5-sunburst', 'gpt-image-2.5-flare', '$imagegen'):
                self.assertEqual(main.gpt_image_2_skill_model_arg(alias, 'codex'),
                                 main.CODEX_DEFAULT_CHAT_MODELS[0])
                self.assertNotEqual(main.gpt_image_2_skill_model_arg(alias, 'codex'), 'gpt-5.4')

    def test_executor_override_and_explicit_model(self):
        with patch.object(main, 'codex_env_value', return_value='custom-executor'):
            self.assertEqual(main.gpt_image_2_skill_model_arg('gpt-image-2', 'codex'), 'custom-executor')
            self.assertEqual(main.gpt_image_2_skill_model_arg('explicit-executor', 'codex'), 'explicit-executor')

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
        detail = "The 'gpt-5.4' model is not supported when using Codex with a ChatGPT account."
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


if __name__ == '__main__':
    unittest.main()
