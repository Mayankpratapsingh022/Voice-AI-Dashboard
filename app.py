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
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Voice Call System",
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
        self.use_cases = {}
        self.default_use_case = ""
        self.current_use_case = ""
        self._load_call_config()
    
    def _load_call_config(self):
        """Load call configuration from JSON file."""
        try:
            with open('call_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.use_cases = config.get('use_cases', {})
            self.default_use_case = config.get('default_use_case', 'emi_collection')
            self.current_use_case = self.default_use_case
            
        except FileNotFoundError:
            st.error("call_config.json not found. Please create the configuration file.")
        except json.JSONDecodeError as e:
            st.error(f"Error parsing call_config.json: {e}")
    
    def get_current_config(self):
        """Get configuration for the current use case."""
        if self.current_use_case in self.use_cases:
            return self.use_cases[self.current_use_case]
        return {}
    
    def get_customer_info(self):
        """Get customer info for current use case."""
        config = self.get_current_config()
        return config.get('customer_info', {})
    
    def get_call_settings(self):
        """Get call settings for current use case."""
        config = self.get_current_config()
        return config.get('call_settings', {})
    
    def get_ai_prompt(self):
        """Get AI prompt for current use case."""
        config = self.get_current_config()
        return config.get('ai_prompt', '')
    
    def get_use_case_names(self):
        """Get list of available use case names."""
        return list(self.use_cases.keys())
    
    def get_use_case_info(self, use_case_key):
        """Get use case information."""
        if use_case_key in self.use_cases:
            use_case = self.use_cases[use_case_key]
            return {
                'name': use_case.get('name', use_case_key),
                'description': use_case.get('description', ''),
                'customer_info': use_case.get('customer_info', {}),
                'call_settings': use_case.get('call_settings', {}),
                'ai_prompt': use_case.get('ai_prompt', '')
            }
        return {}
    
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
        
        return missing
    
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
        """Print minimal configuration summary"""
        st.info(f"""
        **Call Details:**
        - **Calling:** {destination_phone} ({customer_name})
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
    if 'selected_use_case' not in st.session_state:
        st.session_state.selected_use_case = st.session_state.call_system.default_use_case
    
    # Use Case Selection
    st.markdown('<h2 class="section-header">Use Case Selection</h2>', unsafe_allow_html=True)
    
    use_case_options = {}
    for key in st.session_state.call_system.get_use_case_names():
        use_case_info = st.session_state.call_system.get_use_case_info(key)
        use_case_options[key] = f"{use_case_info['name']} - {use_case_info['description']}"
    
    selected_use_case = st.selectbox(
        "Select Use Case",
        options=list(use_case_options.keys()),
        format_func=lambda x: use_case_options[x],
        index=list(use_case_options.keys()).index(st.session_state.selected_use_case) if st.session_state.selected_use_case in use_case_options else 0
    )
    
    # Update current use case if changed
    if selected_use_case != st.session_state.selected_use_case:
        st.session_state.selected_use_case = selected_use_case
        st.session_state.call_system.current_use_case = selected_use_case
        st.rerun()
    
    # Show current use case info
    current_info = st.session_state.call_system.get_use_case_info(selected_use_case)
    st.info(f"**Current Use Case:** {current_info['name']} - {current_info['description']}")
    
    # Basic Configuration
    st.markdown('<h2 class="section-header">Call Configuration</h2>', unsafe_allow_html=True)
    
    destination_phone = st.text_input(
        "Destination Phone Number",
        value=st.session_state.call_system.get_customer_info().get('phone_number', ''),
        help="Phone number to call (include country code)"
    )
    
    call_settings = st.session_state.call_system.get_call_settings()
    twilio_phone = call_settings.get('twilio_phone_number', '+16416663498')
    st.text_input(
        "Twilio Phone Number",
        value=twilio_phone,
        help="Configured Twilio phone number used to place calls",
        disabled=True
    )
    st.caption(f"You will receive a call from {twilio_phone}.")
    
    # Voice configuration is read-only and comes from call_config.json
    json_voice_config = call_settings.get('voice', {})
    if isinstance(json_voice_config, dict):
        voice_config = json_voice_config
    else:
        voice_config = {
            "provider": "built-in",
            "voice": json_voice_config or "Maansvi"
        }
    
    # AI Model Configuration
    st.markdown('<h3 class="section-header">AI Model Settings</h3>', unsafe_allow_html=True)
    
    temperature = st.slider("Temperature", 0.0, 1.0, st.session_state.call_system.get_call_settings().get('temperature', 0.3), 0.1)
    
    # Customer Information
    st.markdown('<h2 class="section-header">Customer Information</h2>', unsafe_allow_html=True)
    
    customer_name = st.text_input("Customer Name", value=st.session_state.call_system.get_customer_info().get('name', 'Amit Lodha'))
    customer_gender = st.selectbox("Gender", ["Male", "Female"], index=["Male", "Female"].index(st.session_state.call_system.get_customer_info().get('gender', 'Male')))
    
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
    
    # Configuration Status
    st.markdown('<h2 class="section-header">Configuration Status</h2>', unsafe_allow_html=True)
    
    missing_creds = st.session_state.call_system.validate_credentials()
    
    if missing_creds:
        st.error("Requirements missing. Please update `streamlit/secrets.toml`.")
    else:
        st.success("Requirements are successful.")
    
    # Call Controls
    st.markdown('<h2 class="section-header">Call Controls</h2>', unsafe_allow_html=True)
    
    if st.button("Initiate Call", type="primary", use_container_width=True):
            missing_creds = st.session_state.call_system.validate_credentials()
            
            if missing_creds:
                st.error(f"Required API keys missing: {', '.join(missing_creds)}")
                st.info("Please add these credentials before initiating a call.")
            
            if not missing_creds:
                # Create customer data dictionary using JSON config as base
                customer_data = st.session_state.call_system.get_customer_info().copy()
                customer_data.update({
                    "name": customer_name,
                    "phone_number": destination_phone,
                    "gender": customer_gender
                })
                
                # Add custom parameters
                for param in st.session_state.custom_params:
                    customer_data[param['key']] = param['value']
                
                system_prompt = st.session_state.call_system.get_ai_prompt()
                
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
                            st.markdown(f"**Customer ({message['timestamp']}):** {message['text']}")
                        else:
                            st.markdown(f"**AI Agent ({message['timestamp']}):** {message['text']}")

if __name__ == "__main__":
    main()