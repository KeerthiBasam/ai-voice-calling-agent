"""
LangGraph voice agent workflow.

Flow:
  receive_call -> transcribe_audio -> understand_intent
-> call_scheduler_tool -> generate_response -> synthesize_voice -> end_call
-> human_handoff -> end_call
"""

import logging
  from typing import TypedDict, Optional, List
    from langgraph.graph import StateGraph, END

      from app.models.schemas import AgentState, ConversationTurn
        from app.services import session_memory
          from app.services.llm_service import generate_response
            from app.services.tts_service import synthesize_speech
              from app.tools.scheduler_tools import check_availability, book_appointment
                from app.tools.crm_tools import get_customer_context
                  from app.config import settings

                    logger = logging.getLogger(__name__)


                    class VoiceAgentState(TypedDict):
                          session_id: str
                          caller_phone: str
                          transcript: str
                          confidence: float
                          intent: str
                          context: str
                      history: List[dict]
                          collected_info: dict
                          agent_text: str
                          audio_url: str
                      booking_result: Optional[dict]
                          handoff_triggered: bool
                          current_state: str


                      def node_receive_call(state: VoiceAgentState) -> VoiceAgentState:
                          """Initialize session and fetch CRM context."""
                      ctx = session_memory.get_or_create_session(state["session_id"], state["caller_phone"])
                      crm_context = get_customer_context(state["caller_phone"])
                      logger.info(f"[GRAPH] receive_call session={state['session_id']}")
                      return {
                                **state,
                                "context": crm_context,
                        "history": [t.model_dump() for t in ctx.history],
                                  "collected_info": ctx.collected_info,
                                  "current_state": AgentState.receive_call,
                                    }


                          def node_transcribe_audio(state: VoiceAgentState) -> VoiceAgentState:
                              """Normalize transcript and add to history."""
                          transcript = state.get("transcript", "").strip()
                          session_id = state["session_id"]
                          history = state["history"]
                              if transcript:
                                session_memory.append_turn(session_id, "user", transcript)
                                history = history + [{"role": "user", "content": transcript}]
                                logger.info(f"[GRAPH] transcribe_audio: '{transcript}'")
                                return {**state, "history": history, "current_state": AgentState.transcribe_audio}


                                def node_understand_intent(state: VoiceAgentState) -> VoiceAgentState:
                                    """Simple keyword-based intent detection."""
                                text = state.get("transcript", "").lower()
                                confidence = state.get("confidence", 1.0)
                                if any(w in text for w in ["book", "schedule", "appointment", "tomorrow", "morning", "afternoon"]):
                                          intent = "book_appointment"
                                  elif any(w in text for w in ["cancel", "reschedule"]):
                                            intent = "cancel_appointment"
                                    elif any(w in text for w in ["human", "agent", "transfer", "person"]):
                                              intent = "human_handoff"
                                          elif confidence < settings.CONFIDENCE_THRESHOLD:
                                              intent = "unclear"
                                          else:
                                                    intent = "general"

                                            collected = state.get("collected_info", {})
                                                if "tomorrow" in text:
                                                  collected["preferred_date"] = "tomorrow"
                                                      if "afternoon" in text:
                                                        collected["preferred_time"] = "afternoon"
                                                            elif "morning" in text:
                                                        collected["preferred_time"] = "morning"

                                                        session_memory.update_collected_info(state["session_id"], collected)
                                                        logger.info(f"[GRAPH] understand_intent: {intent}")
                                                        return {**state, "intent": intent, "collected_info": collected, "current_state": AgentState.understand_intent}


                                                        def node_call_scheduler_tool(state: VoiceAgentState) -> VoiceAgentState:
                                                            """Check availability and book if confirmed."""
                                                        collected = state.get("collected_info", {})
                                                        preferred_date = collected.get("preferred_date", "tomorrow")
                                                        preferred_time = collected.get("preferred_time", "afternoon")
                                                        availability = check_availability(preferred_date, preferred_time)
                                                            booking_result = None
                                                        if availability["available"] and collected.get("confirmed"):
                                                          booking_result = book_appointment(
                                                            caller_phone=state["caller_phone"],
                                                                        preferred_date=preferred_date,
                                                                        preferred_time=preferred_time,
                                                            name=collected.get("name"),
                                                          )
                                                          if booking_result["success"]:
                                                            session_memory.update_collected_info(state["session_id"], {"booking_id": booking_result["booking_id"]})
                                                            logger.info(f"[GRAPH] call_scheduler_tool: available={availability['available']}")
                                                            return {
                                                                      **state,
                                                                      "booking_result": booking_result,
                                                              "collected_info": {**collected, "availability": availability},
                                                                      "current_state": AgentState.call_scheduler_tool,
                                                            }


                                                            async def node_generate_response(state: VoiceAgentState) -> VoiceAgentState:
                                                                """Generate LLM response."""
                                                            session_id = state["session_id"]
                                                            context_parts = [state.get("context", "")]
                                                            booking = state.get("booking_result")
                                                            availability = state.get("collected_info", {}).get("availability", {})
                                                            if booking and booking.get("success"):
                                                              context_parts.append(f"Booking confirmed: {booking['confirmed_slot']} ID={booking['booking_id']}")
                                                                  elif availability:
                                                              slots = availability.get("available_slots", [])
                                                              context_parts.append(f"Available slots: {', '.join(slots[:3])}")
                                                              context = " | ".join(filter(None, context_parts))
                                                              text_response = await generate_response(state.get("history", []), context, session_id)
                                                              session_memory.append_turn(session_id, "assistant", text_response)
                                                              session_memory.update_state(session_id, AgentState.generate_response)
                                                              return {
                                                                        **state,
                                                                        "agent_text": text_response,
                                                                "history": state.get("history", []) + [{"role": "assistant", "content": text_response}],
                                                                        "current_state": AgentState.generate_response,
                                                              }


                                                              async def node_synthesize_voice(state: VoiceAgentState) -> VoiceAgentState:
                                                                  """Convert agent text to speech."""
                                                              audio_url = await synthesize_speech(state.get("agent_text", ""), state["session_id"])
                                                              return {**state, "audio_url": audio_url, "current_state": AgentState.synthesize_voice}


                                                              async def node_human_handoff(state: VoiceAgentState) -> VoiceAgentState:
                                                                  """Trigger human handoff."""
                                                                  msg = "I'm going to connect you with one of our team members now. Please hold on for just a moment."
                                                              audio_url = await synthesize_speech(msg, state["session_id"])
                                                              session_memory.update_state(state["session_id"], AgentState.human_handoff)
                                                              return {**state, "agent_text": msg, "audio_url": audio_url, "handoff_triggered": True, "current_state": AgentState.human_handoff}


                                                              def node_end_call(state: VoiceAgentState) -> VoiceAgentState:
                                                                  """Finalize session."""
                                                              session_memory.update_state(state["session_id"], AgentState.end_call)
                                                              logger.info(f"[GRAPH] end_call session={state['session_id']}")
                                                              return {**state, "current_state": AgentState.end_call}


                                                              def route_after_intent(state: VoiceAgentState) -> str:
                                                              intent = state.get("intent", "general")
                                                              confidence = state.get("confidence", 1.0)
                                                                  if intent == "human_handoff" or intent == "unclear" or confidence < settings.CONFIDENCE_THRESHOLD:
                                                                            return "human_handoff"
                                                                    if intent in ("book_appointment", "cancel_appointment"):
                                                                              return "call_scheduler_tool"
                                                                          return "generate_response"


                                                                      def build_voice_agent_graph() -> StateGraph:
                                                                      graph = StateGraph(VoiceAgentState)
                                                                      graph.add_node("receive_call", node_receive_call)
                                                                      graph.add_node("transcribe_audio", node_transcribe_audio)
                                                                      graph.add_node("understand_intent", node_understand_intent)
                                                                      graph.add_node("call_scheduler_tool", node_call_scheduler_tool)
                                                                      graph.add_node("generate_response", node_generate_response)
                                                                      graph.add_node("synthesize_voice", node_synthesize_voice)
                                                                      graph.add_node("human_handoff", node_human_handoff)
                                                                      graph.add_node("end_call", node_end_call)
                                                                      graph.set_entry_point("receive_call")
                                                                      graph.add_edge("receive_call", "transcribe_audio")
                                                                      graph.add_edge("transcribe_audio", "understand_intent")
                                                                      graph.add_conditional_edges(
                                                                                "understand_intent",
                                                                                route_after_intent,
                                                                        {
                                                                                      "call_scheduler_tool": "call_scheduler_tool",
                                                                                      "generate_response": "generate_response",
                                                                                      "human_handoff": "human_handoff",
                                                                        },
                                                                      )
                                                                      graph.add_edge("call_scheduler_tool", "generate_response")
                                                                      graph.add_edge("generate_response", "synthesize_voice")
                                                                      graph.add_edge("synthesize_voice", "end_call")
                                                                      graph.add_edge("human_handoff", "end_call")
                                                                      graph.add_edge("end_call", END)
                                                                      return graph.compile()


                                                                      voice_agent = build_voice_agent_graph()
                                                                      
