from rest_framework.renderers import JSONRenderer

class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        status_code = response.status_code if response else 200

        # Pass through if already in destination format
        if isinstance(data, dict) and 'status' in data and 'message' in data and 'data' in data:
            return super().render(data, accepted_media_type, renderer_context)

        # Build custom wrapper
        is_success = status_code < 400
        custom_response = {
            'status': is_success,
            'message': 'Success' if is_success else 'Error',
            'data': {}
        }

        if not is_success:
            if isinstance(data, dict):
                if 'detail' in data:
                    custom_response['message'] = str(data['detail'])
                elif data:
                    first_key = list(data.keys())[0]
                    first_val = data[first_key]
                    if isinstance(first_val, list) and len(first_val) > 0:
                        custom_response['message'] = f"{first_key}: {first_val[0]}"
                    else:
                        custom_response['message'] = f"{first_key}: {first_val}"
            custom_response['data'] = data
        else:
            custom_response['data'] = data if data is not None else {}

        return super().render(custom_response, accepted_media_type, renderer_context)
