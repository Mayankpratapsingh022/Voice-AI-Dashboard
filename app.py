"""
Ultravox-Twilio Call System with ElevenLabs TTS - Complete Streamlit Web App
A comprehensive web interface for configuring and triggering AI-powered phone calls.
All functionality integrated into a single file.
"""

import streamlit as st
import requests
import time
import json
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect
from typing import Dict, Any, Optional
import threading
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Voice Call System",
    page_icon="📞",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        color: #1f77b4;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #2c3e50;
    }
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.375rem;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.375rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class UltravoxTwilioCallSystem:
    """Complete Ultravox-Twilio call system with ElevenLabs TTS integration."""
    
    def __init__(self):
        # Load credentials from Streamlit secrets only
        # Access secrets directly since they're under [secrets] section
        secrets = st.secrets.get("secrets", {})
        self.twilio_account_sid = secrets.get('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = secrets.get('TWILIO_AUTH_TOKEN')
        self.ultravox_api_key = secrets.get('ULTRAVOX_API_KEY')
        self.elevenlabs_api_key = secrets.get('ELEVENLABS_API_KEY')
        self.ultravox_api_url = secrets.get('ULTRAVOX_API_URL', 'https://api.ultravox.ai/api/calls')
        
        # Load configuration from JSON file
        self.customer_info = {}
        self.call_settings = {}
        self.ai_prompt = ""
        self._load_call_config()
    
    def _load_call_config(self):
        """Load call configuration from JSON file."""
        try:
            with open('call_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.customer_info = config.get('customer_info', {})
            self.call_settings = config.get('call_settings', {})
            self.ai_prompt = config.get('ai_prompt', '')
            
        except FileNotFoundError:
            st.error("call_config.json not found. Please create the configuration file.")
        except json.JSONDecodeError as e:
            st.error(f"Error parsing call_config.json: {e}")
    
    def validate_credentials(self):
        """Validate that all required credentials are set"""
        missing = []
        if not self.twilio_account_sid:
            missing.append("TWILIO_ACCOUNT_SID")
        if not self.twilio_auth_token:
            missing.append("TWILIO_AUTH_TOKEN")
        if not self.ultravox_api_key:
            missing.append("ULTRAVOX_API_KEY")
        if not self.elevenlabs_api_key:
            missing.append("ELEVENLABS_API_KEY")
        
        # Check for optional configurations
        optional_missing = []
        secrets = st.secrets.get("secrets", {})
        if not secrets.get('OPENAI_API_KEY'):
            optional_missing.append("OPENAI_API_KEY")
        if not secrets.get('ANTHROPIC_API_KEY'):
            optional_missing.append("ANTHROPIC_API_KEY")
        if not secrets.get('GOOGLE_API_KEY'):
            optional_missing.append("GOOGLE_API_KEY")
            
        return missing, optional_missing
    
    def get_formatted_prompt(self, prompt_template, customer_data):
        """Format the AI prompt with customer data substituted."""
        formatted_prompt = prompt_template
        
        # Replace all placeholders with actual values
        for key, value in customer_data.items():
            placeholder = f"{{{{{key}}}}}"
            formatted_prompt = formatted_prompt.replace(placeholder, str(value))
        
        return formatted_prompt
    
    def get_ultravox_config(self, system_prompt, voice_config, model="fixie-ai/ultravox", temperature=0.3):
        """Generate Ultravox configuration"""
        config = {
            "systemPrompt": system_prompt,
            "model": model,
            "temperature": temperature,
            "firstSpeakerSettings": {"user": {}}, 
            "medium": {"twilio": {}} 
        }
        
        # Handle voice configuration
        if voice_config.get('provider') == 'elevenlabs':
            config["voice"] = None
            config["externalVoice"] = {
                "elevenLabs": {
                    "voiceId": voice_config.get('voiceId', '21m00Tcm4TlvDq8ikWAM'),
                    "model": voice_config.get('model', 'eleven_turbo_v2_5')
                }
            }
        else:
            config["voice"] = voice_config.get('voice', 'Maansvi')
            
        return config
    
    def initiate_call(self, destination_phone, twilio_phone, system_prompt, voice_config, model, temperature):
        """Initiate Ultravox call"""
        try:
            # Create Ultravox call session
            ultravox_config = self.get_ultravox_config(system_prompt, voice_config, model, temperature)
            
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.ultravox_api_key
            }
            
            response = requests.post(self.ultravox_api_url, json=ultravox_config, headers=headers)
            response.raise_for_status()
            ultravox_response = response.json()
            ultravox_join_url = ultravox_response.get("joinUrl")
            ultravox_call_id = ultravox_response.get("callId")
            
            if not ultravox_join_url:
                raise ValueError("Ultravox API did not return a valid joinUrl.")
            
            # Initiate Twilio call
            twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            response_twiml = VoiceResponse()
            connect = Connect()
            connect.stream(url=ultravox_join_url)
            response_twiml.append(connect)
            twiml_string = str(response_twiml)

            call = twilio_client.calls.create(
                twiml=twiml_string,
                to=destination_phone,
                from_=twilio_phone
            )
            
            return {
                "success": True,
                "ultravox_call_id": ultravox_call_id,
                "twilio_call_sid": call.sid,
                "message": f"Call initiated successfully! Twilio SID: {call.sid}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def fetch_transcript(self, call_id, max_wait_seconds=120):
        """Fetch call transcript"""
        headers = {'X-API-Key': self.ultravox_api_key}
        call_status_url = f"{self.ultravox_api_url}/{call_id}"
        
        poll_interval = 5 
        max_iterations = max_wait_seconds // poll_interval
        
        for i in range(max_iterations):
            time.sleep(poll_interval)
            
            try:
                response = requests.get(call_status_url, headers=headers)
                response.raise_for_status()
                call_details = response.json()
                
                if call_details.get("ended"):
                    messages_url = f"{call_status_url}/messages"
                    messages_response = requests.get(messages_url, headers=headers)
                    messages_response.raise_for_status()
                    messages = messages_response.json().get('results', [])
                    
                    transcript = []
                    for message in messages:
                        role = message.get("role", "UNKNOWN").replace("MESSAGE_ROLE_", "")
                        text = message.get("text", "")
                        
                        if text and role in ["AGENT", "USER"]:
                            transcript.append({
                                "role": role,
                                "text": text,
                                "timestamp": datetime.now().strftime("%H:%M:%S")
                            })
                    
                    return {
                        "success": True,
                        "transcript": transcript,
                        "end_reason": call_details.get('endReason')
                    }
                    
            except requests.exceptions.RequestException as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        return {
            "success": False,
            "error": "Max wait time exceeded"
        }
    
    def print_config_summary(self, customer_name, destination_phone, voice_config):
        """Print configuration summary"""
        st.info(f"""
        **Configuration Summary:**
        - **Calling:** {destination_phone} ({customer_name})
        - **Voice:** {voice_config.get('provider', 'built-in')} - {voice_config.get('voiceId', voice_config.get('voice', 'Unknown'))}
        - **Model:** fixie-ai/ultravox
        """)

def main():
    # Header
    st.markdown('<h1 class="main-header">Voice Call System</h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'call_system' not in st.session_state:
        st.session_state.call_system = UltravoxTwilioCallSystem()
    if 'custom_params' not in st.session_state:
        st.session_state.custom_params = []
    if 'call_history' not in st.session_state:
        st.session_state.call_history = []
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Basic Configuration
        st.markdown('<h2 class="section-header">Call Configuration</h2>', unsafe_allow_html=True)
        
        destination_phone = st.text_input("Destination Phone Number", value=st.session_state.call_system.customer_info.get('phone_number', ''), help="Phone number to call (include country code)")
        twilio_phone = st.text_input("Twilio Phone Number", value=st.session_state.call_system.call_settings.get('twilio_phone_number', '+16416663498'), help="Your Twilio phone number")
        
        # Voice Configuration
        st.markdown('<h3 class="section-header">Voice Settings</h3>', unsafe_allow_html=True)
        
        # Get voice config from JSON
        json_voice_config = st.session_state.call_system.call_settings.get('voice', {})
        
        if isinstance(json_voice_config, dict) and json_voice_config.get('provider') == 'elevenlabs':
            voice_provider = st.selectbox("Voice Provider", ["elevenlabs", "built-in"], index=0)
        else:
            voice_provider = st.selectbox("Voice Provider", ["elevenlabs", "built-in"], index=1)
        
        voice_config = {}
        if voice_provider == "elevenlabs":
            voice_id = st.text_input("ElevenLabs Voice ID", value=json_voice_config.get('voiceId', 'z3L1naUiX6l4xiMWzigO'))
            voice_model = st.selectbox("ElevenLabs Model", ["eleven_turbo_v2_5", "eleven_multilingual_v2", "eleven_monolingual_v1"], 
                                     index=["eleven_turbo_v2_5", "eleven_multilingual_v2", "eleven_monolingual_v1"].index(json_voice_config.get('model', 'eleven_turbo_v2_5')))
            voice_config = {
                "provider": "elevenlabs",
                "voiceId": voice_id,
                "model": voice_model
            }
        else:
            built_in_voice = st.text_input("Built-in Voice Name", value=json_voice_config.get('voice', 'Maansvi'))
            voice_config = {
                "provider": "built-in",
                "voice": built_in_voice
            }
        
        # AI Model Configuration
        st.markdown('<h3 class="section-header">AI Model Settings</h3>', unsafe_allow_html=True)
        
        temperature = st.slider("Temperature", 0.0, 1.0, st.session_state.call_system.call_settings.get('temperature', 0.3), 0.1)
        
        # Customer Information
        st.markdown('<h2 class="section-header">Customer Information</h2>', unsafe_allow_html=True)
        
        customer_name = st.text_input("Customer Name", value=st.session_state.call_system.customer_info.get('name', 'Amit Lodha'))
        customer_gender = st.selectbox("Gender", ["Male", "Female"], index=["Male", "Female"].index(st.session_state.call_system.customer_info.get('gender', 'Male')))
        
        # Dynamic Custom Parameters
        st.markdown('<h3 class="section-header">Custom Parameters</h3>', unsafe_allow_html=True)
        
        col_param1, col_param2, col_param3 = st.columns([2, 2, 1])
        
        with col_param1:
            param_key = st.text_input("Parameter Key", placeholder="e.g., loan_amount")
        with col_param2:
            param_value = st.text_input("Parameter Value", placeholder="e.g., 50000")
        with col_param3:
            if st.button("Add Parameter"):
                if param_key and param_value:
                    st.session_state.custom_params.append({"key": param_key, "value": param_value})
                    st.rerun()
        
        # Display current custom parameters
        if st.session_state.custom_params:
            st.write("**Current Custom Parameters:**")
            for i, param in enumerate(st.session_state.custom_params):
                col_display1, col_display2, col_display3 = st.columns([2, 2, 1])
                with col_display1:
                    st.write(f"**{param['key']}:**")
                with col_display2:
                    st.write(param['value'])
                with col_display3:
                    if st.button("Remove", key=f"remove_{i}"):
                        st.session_state.custom_params.pop(i)
                        st.rerun()
    
    with col2:
        # System Prompt
        st.markdown('<h2 class="section-header">System Prompt</h2>', unsafe_allow_html=True)
        
        # Load prompt from JSON config
        system_prompt = st.text_area("System Prompt", value=st.session_state.call_system.ai_prompt, height=400)
        
        # Generate formatted prompt
        if st.button("Preview Formatted Prompt"):
            # Create customer data dictionary using JSON config as base
            customer_data = st.session_state.call_system.customer_info.copy()
            customer_data.update({
                "name": customer_name,
                "phone_number": destination_phone,
                "gender": customer_gender
            })
            
            # Add custom parameters
            for param in st.session_state.custom_params:
                customer_data[param['key']] = param['value']
            
            # Format the prompt
            formatted_prompt = st.session_state.call_system.get_formatted_prompt(system_prompt, customer_data)
            
            st.text_area("Formatted Prompt Preview", value=formatted_prompt, height=200)
    
    # Configuration Status
    st.markdown('<h2 class="section-header">Configuration Status</h2>', unsafe_allow_html=True)
    
    # Show secrets source
    st.info("🔐 **Using Streamlit Secrets** (from `streamlit/secrets.toml`)")
    
    missing_creds, optional_missing = st.session_state.call_system.validate_credentials()
    
    col_status1, col_status2 = st.columns(2)
    
    with col_status1:
        st.subheader("✅ Required APIs")
        required_apis = [
            ("TWILIO_ACCOUNT_SID", "Twilio Account"),
            ("TWILIO_AUTH_TOKEN", "Twilio Auth"),
            ("ULTRAVOX_API_KEY", "Ultravox API"),
            ("ELEVENLABS_API_KEY", "ElevenLabs API")
        ]
        
        for api_key, api_name in required_apis:
            if api_key not in missing_creds:
                st.success(f"✅ {api_name}")
            else:
                st.error(f"❌ {api_name}")
    
    with col_status2:
        st.subheader("💡 Optional APIs")
        optional_apis = [
            ("OPENAI_API_KEY", "OpenAI API"),
            ("ANTHROPIC_API_KEY", "Anthropic API"),
            ("GOOGLE_API_KEY", "Google API")
        ]
        
        for api_key, api_name in optional_apis:
            if api_key not in optional_missing:
                st.success(f"✅ {api_name}")
            else:
                st.info(f"ℹ️ {api_name} (not configured)")
    
    # Call Controls
    st.markdown('<h2 class="section-header">Call Controls</h2>', unsafe_allow_html=True)
    
    if st.button("Initiate Call", type="primary", use_container_width=True):
            missing_creds, optional_missing = st.session_state.call_system.validate_credentials()
            
            if missing_creds:
                st.error(f"⚠️ **Required sAPI keys missing:** {', '.join(missing_creds)}")
                st.info("Please add these to your `streamlit/secrets.toml` file")
            
            if optional_missing:
                st.warning(f"💡 **Optional API keys not configured:** {', '.join(optional_missing)}")
                st.info("These are optional but may be needed for advanced features")
            
            if not missing_creds:
                # Create customer data dictionary using JSON config as base
                customer_data = st.session_state.call_system.customer_info.copy()
                customer_data.update({
                    "name": customer_name,
                    "phone_number": destination_phone,
                    "gender": customer_gender
                })
                
                # Add custom parameters
                for param in st.session_state.custom_params:
                    customer_data[param['key']] = param['value']
                
                # Format the prompt
                formatted_prompt = st.session_state.call_system.get_formatted_prompt(system_prompt, customer_data)
                
                # Show configuration summary
                st.session_state.call_system.print_config_summary(customer_name, destination_phone, voice_config)
                
                # Initiate call
                with st.spinner("Initiating call..."):
                    result = st.session_state.call_system.initiate_call(
                        destination_phone, twilio_phone, formatted_prompt, 
                        voice_config, "fixie-ai/ultravox", temperature
                    )
                
                if result["success"]:
                    st.success(result["message"])
                    st.session_state.ultravox_call_id = result["ultravox_call_id"]
                    st.session_state.twilio_call_sid = result["twilio_call_sid"]
                    
                    # Add to call history
                    call_entry = {
                        "call_id": result["ultravox_call_id"],
                        "twilio_sid": result["twilio_call_sid"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "customer_name": customer_name,
                        "destination_phone": destination_phone,
                        "status": "initiated"
                    }
                    st.session_state.call_history.append(call_entry)
                else:
                    st.error(f"Call failed: {result['error']}")
    
    # Status Information
    if 'ultravox_call_id' in st.session_state:
        st.markdown('<h3 class="section-header">Call Status</h3>', unsafe_allow_html=True)
        st.info(f"**Active Call ID:** {st.session_state.ultravox_call_id}")
        if 'twilio_call_sid' in st.session_state:
            st.info(f"**Twilio Call SID:** {st.session_state.twilio_call_sid}")
    
    # Call History
    if st.session_state.call_history:
        st.markdown('<h2 class="section-header">Call History</h2>', unsafe_allow_html=True)
        
        for i, call in enumerate(reversed(st.session_state.call_history)):
            with st.expander(f"Call {len(st.session_state.call_history) - i} - {call['timestamp']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Call ID:** {call['call_id']}")
                    st.write(f"**Customer:** {call['customer_name']}")
                    st.write(f"**Phone:** {call['destination_phone']}")
                    st.write(f"**Status:** {call['status']}")
                
                with col2:
                    st.write(f"**Timestamp:** {call['timestamp']}")
                    if 'twilio_sid' in call:
                        st.write(f"**Twilio SID:** {call['twilio_sid']}")
                    if 'end_reason' in call:
                        st.write(f"**End Reason:** {call['end_reason']}")
                
                # Display transcript if available
                if 'transcript' in call and call['transcript']:
                    st.subheader("Conversation Transcript")
                    for message in call['transcript']:
                        if message['role'] == 'USER':
                            st.markdown(f"**👤 Customer ({message['timestamp']}):** {message['text']}")
                        else:
                            st.markdown(f"**🤖 AI Agent ({message['timestamp']}):** {message['text']}")

if __name__ == "__main__":
    main()