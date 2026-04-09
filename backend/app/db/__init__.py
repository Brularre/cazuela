from supabase import create_client
from app.config import settings

client = create_client(settings.supabase_url, settings.supabase_key)
