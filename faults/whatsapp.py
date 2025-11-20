import requests
from django.conf import settings

def send_whatsapp_message(phone_number: str = None, message: str = "", image_path: str = None) -> bool:
    """
    Send a WhatsApp message using Meta's WhatsApp Cloud API.

    Args:
        phone_number: Recipient's phone number in international format (e.g., "91XXXXXXXXXX").
                      If None, uses WHATSAPP_DEFAULT_NUMBER from settings.
        message: Text message to send.
        image_path: Optional local image path to send with the message. Will be converted to public URL.

    Returns:
        True if message sent successfully, False otherwise.
    """
    try:
        # Use default number if none provided
        if phone_number is None:
            phone_number = getattr(settings, "WHATSAPP_DEFAULT_NUMBER", None)
            if not phone_number:
                print("❌ No phone number provided and WHATSAPP_DEFAULT_NUMBER not set in settings.")
                return False

        # Construct API request
        url = settings.WHATSAPP_API_URL
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
        }

        if image_path:
            # Construct public URL for the image
            image_url = f"{settings.SITE_URL}/static/fault_images/{image_path.split('/')[-1]}"
            payload["type"] = "image"
            payload["image"] = {
                "link": image_url,
                "caption": message
            }
        else:
            payload["type"] = "text"
            payload["text"] = {"body": message}

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code in [200, 201]:
            print(f"✅ WhatsApp message sent to {phone_number}")
            return True
        else:
            print(f"❌ Failed to send message to {phone_number}: {response.status_code}, {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception occurred while sending WhatsApp message: {str(e)}")
        return False
