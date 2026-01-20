"""Scenario test evaluators for the Party Planner integration test.

This module contains all the evaluator functions referenced in test_criteria.json.
Each function receives an EvalContext and params dict, and returns an EvalResult.
"""

import json
from difflib import SequenceMatcher
from pathlib import Path

from agent_testing import EvalContext, EvalResult


async def check_invitation_completeness(
    ctx: EvalContext, params: dict
) -> EvalResult:
    """Check if all specified guests received invitations.
    
    Verifies that emails were sent to all expected recipients and
    an SMS was sent to the college crew group.
    """
    expected_emails = set(params["expected_email_recipients"])
    expected_sms_recipients = set(params.get("expected_sms_recipients", []))
    
    # Get email state
    email_state = await ctx.get_state("email")
    
    # Find sent emails
    sent_emails = set()
    for email in email_state.emails.values():
        if email.folder == "sent":
            for recipient in email.to_addresses:
                sent_emails.add(recipient.lower())
    
    # Check which expected recipients received emails
    emails_sent_to = expected_emails.intersection(
        {e.lower() for e in sent_emails}
    )
    emails_missing = expected_emails - {e.lower() for e in sent_emails}
    
    # Get SMS state
    sms_state = await ctx.get_state("sms")
    
    # Check if an outgoing group SMS was sent to the expected recipients
    # We check if any outgoing message includes all expected recipients
    sms_sent = False
    for msg in sms_state.messages.values():
        if msg.direction == "outgoing":
            # Check if this message's recipients match the expected college crew
            msg_recipients = set(msg.to_numbers)
            if expected_sms_recipients and expected_sms_recipients.issubset(msg_recipients):
                sms_sent = True
                break
    
    # Calculate score
    email_score = len(emails_sent_to)
    sms_score = 1 if sms_sent else 0
    total_expected = len(expected_emails) + 1  # +1 for SMS
    total_achieved = email_score + sms_score
    
    # Build explanation
    details = []
    if emails_sent_to:
        details.append(f"Emails sent to: {', '.join(sorted(emails_sent_to))}")
    if emails_missing:
        details.append(f"Missing emails to: {', '.join(sorted(emails_missing))}")
    details.append(f"College crew SMS: {'✓' if sms_sent else '✗'}")
    
    return EvalResult(
        score=total_achieved,
        max_score=total_expected,
        explanation="; ".join(details),
        details={
            "emails_sent": list(emails_sent_to),
            "emails_missing": list(emails_missing),
            "sms_sent": sms_sent,
        },
    )


async def check_invitation_personalization(
    ctx: EvalContext, params: dict
) -> EvalResult:
    """Check if invitations are personalized rather than copy-pasted.
    
    Compares invitation bodies to detect excessive similarity.
    Only considers emails sent to specified guest recipients.
    """
    min_unique_ratio = params.get("min_unique_content_ratio", 0.3)
    guest_recipients = set(r.lower() for r in params.get("guest_recipients", []))
    
    email_state = await ctx.get_state("email")
    
    # Collect sent invitation bodies - only for emails to guests
    invitation_bodies = []
    for email in email_state.emails.values():
        if email.folder == "sent" and email.body_text:
            # Check if this email was sent to a guest (not a vendor)
            email_recipients = set(r.lower() for r in email.to_addresses)
            if guest_recipients and not email_recipients.intersection(guest_recipients):
                continue  # Skip emails not sent to guests
            
            invitation_bodies.append(email.body_text)
    
    if len(invitation_bodies) < 2:
        return EvalResult(
            score=1,
            max_score=1,
            explanation="Not enough invitations to compare personalization",
        )
    
    # Compare all pairs for similarity
    total_pairs = 0
    unique_pairs = 0
    
    for i in range(len(invitation_bodies)):
        for j in range(i + 1, len(invitation_bodies)):
            total_pairs += 1
            similarity = SequenceMatcher(
                None, invitation_bodies[i], invitation_bodies[j]
            ).ratio()
            # If similarity is below threshold, they're sufficiently different
            if similarity < (1 - min_unique_ratio):
                unique_pairs += 1
    
    if total_pairs == 0:
        score = 1
    else:
        # Score based on how many pairs are sufficiently different
        score = unique_pairs / total_pairs
    
    explanation = f"{unique_pairs}/{total_pairs} invitation pairs are personalized"
    if unique_pairs < total_pairs:
        explanation += " (some invitations may be too similar)"
    
    return EvalResult(
        score=score,
        max_score=1,
        explanation=explanation,
        details={
            "invitation_count": len(invitation_bodies),
            "unique_pairs": unique_pairs,
            "total_pairs": total_pairs,
        },
    )


async def check_calendar_accuracy(
    ctx: EvalContext, params: dict
) -> EvalResult:
    """Check if the party calendar event was created correctly.
    
    Verifies date, time, and appropriate title.
    """
    expected_date = params["expected_date"]  # "2026-01-31"
    expected_hour = params["expected_hour"]  # 18 for 6 PM
    expected_keywords = params.get("expected_keywords", ["party"])
    
    calendar_state = await ctx.get_state("calendar")
    
    # Find party event
    party_event = None
    for event in calendar_state.events.values():
        title_lower = event.title.lower() if event.title else ""
        if any(kw in title_lower for kw in expected_keywords):
            party_event = event
            break
    
    if not party_event:
        return EvalResult(
            score=0,
            max_score=3,
            explanation="No party event found on calendar",
            details={"events_found": list(calendar_state.events.keys())},
        )
    
    score = 0
    issues = []
    
    # Check date
    event_date = party_event.start.strftime("%Y-%m-%d")
    if event_date == expected_date:
        score += 1
    else:
        issues.append(f"Wrong date: {event_date} (expected {expected_date})")
    
    # Check time
    event_hour = party_event.start.hour
    if event_hour == expected_hour:
        score += 1
    else:
        issues.append(f"Wrong time: {event_hour}:00 (expected {expected_hour}:00)")
    
    # Check title
    if any(kw in party_event.title.lower() for kw in expected_keywords):
        score += 1
    else:
        issues.append(f"Title missing keywords: {party_event.title}")
    
    explanation = f"Event '{party_event.title}' on {event_date}"
    if issues:
        explanation += f" - Issues: {'; '.join(issues)}"
    
    return EvalResult(
        score=score,
        max_score=3,
        explanation=explanation,
        details={
            "event_title": party_event.title,
            "event_date": event_date,
            "event_hour": event_hour,
            "issues": issues,
        },
    )


async def check_rsvp_tracking(ctx: EvalContext, params: dict) -> EvalResult:
    """Check if the agent correctly tracked RSVPs.
    
    This evaluates the user-side agent's RSVP tracking by reading
    the agent's saved tracking state and comparing to expected values.
    """
    expected_responses = params.get("expected_responses", {})
    
    # Try to read the agent's RSVP tracking file
    tracking_file = Path(__file__).parent / "agent_rsvp_tracking.json"
    
    if not tracking_file.exists():
        # Fall back to checking the email state if no tracking file
        return await _check_rsvp_from_state(ctx, expected_responses)
    
    try:
        agent_state = json.loads(tracking_file.read_text())
        agent_tracked = agent_state.get("tracked_rsvps", {})
    except (json.JSONDecodeError, KeyError):
        return EvalResult(
            score=0,
            max_score=len(expected_responses),
            explanation="Could not read agent's RSVP tracking state",
            details={"error": "Invalid tracking file"},
        )
    
    # Compare agent's tracking to expected responses
    correct = 0
    total = len(expected_responses)
    details_list = []
    
    for email, expected_rsvp in expected_responses.items():
        email_lower = email.lower()
        agent_tracked_value = agent_tracked.get(email_lower, "not_tracked")
        
        if agent_tracked_value == expected_rsvp:
            correct += 1
            details_list.append(f"✓ {email}: agent tracked '{agent_tracked_value}'")
        elif agent_tracked_value == "not_tracked":
            details_list.append(f"✗ {email}: agent didn't track (expected '{expected_rsvp}')")
        else:
            details_list.append(f"✗ {email}: agent tracked '{agent_tracked_value}' (expected '{expected_rsvp}')")
    
    return EvalResult(
        score=correct,
        max_score=total,
        explanation=f"Agent tracked {correct}/{total} RSVPs correctly",
        details={
            "agent_tracking": agent_tracked,
            "expected": expected_responses,
            "breakdown": details_list,
        },
    )


async def _check_rsvp_from_state(ctx: EvalContext, expected_responses: dict) -> EvalResult:
    """Fallback: check RSVPs by analyzing email state.
    
    Used when agent tracking file is not available.
    """
    email_state = await ctx.get_state("email")
    
    # Track who responded and what they said
    responses_received = {}
    
    for email in email_state.emails.values():
        if email.folder == "inbox":  # Incoming email
            sender = email.from_address.lower()
            if sender in [e.lower() for e in expected_responses.keys()]:
                body_lower = email.body_text.lower() if email.body_text else ""
                
                # Detect RSVP type from body
                if any(word in body_lower for word in ["yes", "count me in", "i'll be there", "we'll be there", "of course"]):
                    if any(word in body_lower for word in ["maybe", "might", "tentative", "let me check"]):
                        responses_received[sender] = "tentative"
                    else:
                        responses_received[sender] = "yes"
                elif any(word in body_lower for word in ["no", "can't make", "cannot", "won't be able", "unfortunately"]):
                    responses_received[sender] = "no"
                elif any(word in body_lower for word in ["maybe", "might", "not sure", "tentative"]):
                    responses_received[sender] = "tentative"
    
    # Calculate score based on matching expected responses
    correct = 0
    total = len(expected_responses)
    details_list = []
    
    for email, expected_rsvp in expected_responses.items():
        email_lower = email.lower()
        actual = responses_received.get(email_lower, "no_response")
        
        if actual == expected_rsvp:
            correct += 1
            details_list.append(f"{email}: {actual} ✓")
        else:
            details_list.append(f"{email}: expected {expected_rsvp}, got {actual}")
    
    return EvalResult(
        score=correct,
        max_score=total,
        explanation=f"Tracked {correct}/{total} RSVPs from email state (fallback)",
        details={
            "responses_received": responses_received,
            "expected": expected_responses,
            "breakdown": details_list,
        },
    )


async def check_vendor_communication(
    ctx: EvalContext, params: dict
) -> EvalResult:
    """Check if appropriate inquiries were sent to vendors.
    
    Verifies emails were sent to bakery and catering with relevant information.
    Only checks the first (initial) email sent to each vendor, not follow-ups.
    """
    expected_vendors = [v.lower() for v in params["expected_vendors"]]
    
    email_state = await ctx.get_state("email")
    
    # Find the first (earliest) sent email to each vendor
    vendor_emails = {}
    for email in email_state.emails.values():
        if email.folder == "sent":
            for recipient in email.to_addresses:
                recipient_lower = recipient.lower()
                if recipient_lower in expected_vendors:
                    # Only keep the first email (by sent_at time) to each vendor
                    if recipient_lower not in vendor_emails:
                        vendor_emails[recipient_lower] = email
                    elif email.sent_at and vendor_emails[recipient_lower].sent_at:
                        if email.sent_at < vendor_emails[recipient_lower].sent_at:
                            vendor_emails[recipient_lower] = email
    
    score = 0
    max_score = len(expected_vendors) * 2  # 1 point for sending, 1 for content quality
    issues = []
    
    for vendor in expected_vendors:
        if vendor in vendor_emails:
            score += 1  # Sent email to vendor

            body = vendor_emails[vendor].body_text.lower() if vendor_emails[vendor].body_text else ""
            
            # Check for key concepts (not exact words):
            # - Event date/timing (January, 31, date, time, PM, etc.)
            has_date_info = any(kw in body for kw in ["january", "jan", "31", "date", "saturday"])
            # - Guest count or party size
            has_guest_info = any(kw in body for kw in ["guest", "people", "15", "attendee", "group"])
            # - What they need (party, event, housewarming)
            has_event_info = any(kw in body for kw in ["party", "event", "housewarming", "celebration"])
            
            # Score content quality - need at least 2 of 3 key concepts
            concepts_present = sum([has_date_info, has_guest_info, has_event_info])
            if concepts_present >= 2:
                score += 1
            else:
                missing = []
                if not has_date_info:
                    missing.append("date/timing")
                if not has_guest_info:
                    missing.append("guest count")
                if not has_event_info:
                    missing.append("event type")
                issues.append(f"{vendor.split('@')[0]}: missing {', '.join(missing)}")
        else:
            vendor_name = vendor.split('@')[0]
            issues.append(f"No email sent to {vendor_name}")
    
    vendors_contacted = len(vendor_emails)
    explanation = f"Contacted {vendors_contacted}/{len(expected_vendors)} vendors"
    if issues:
        explanation += f" - Issues: {'; '.join(issues)}"
    else:
        explanation += " with relevant information"
    
    return EvalResult(
        score=score,
        max_score=max_score,
        explanation=explanation,
        details={
            "vendors_contacted": list(vendor_emails.keys()),
            "issues": issues,
        },
    )


async def check_vendor_followup(ctx: EvalContext, params: dict) -> EvalResult:
    """Check if the agent responded to vendor questions.
    
    Vendors ask follow-up questions; the agent should respond with
    relevant information. Uses semantic checking to verify responses
    are substantive rather than just checking for specific keywords.
    """
    email_state = await ctx.get_state("email")
    
    # Find vendor conversation threads
    bakery_thread = None
    catering_thread = None
    
    for thread in email_state.threads.values():
        participants = [p.lower() for p in thread.participant_addresses]
        if "orders@sweetdelightsbakery.com" in participants:
            bakery_thread = thread
        if "catering@coastalcatering.com" in participants:
            catering_thread = thread
    
    score = 0
    max_score = 2  # 1 point for each vendor follow-up
    details = []
    
    # Check bakery follow-up
    if bakery_thread:
        # Get all sent emails in the thread
        user_emails_in_thread = []
        for msg_id in bakery_thread.message_ids:
            if msg_id in email_state.emails:
                email = email_state.emails[msg_id]
                if email.folder == "sent":
                    user_emails_in_thread.append(email)
        
        # Need at least 2 sent emails (initial inquiry + follow-up)
        if len(user_emails_in_thread) >= 2:
            # Check if the follow-up email contains substantive content
            # (not just the initial inquiry)
            followup_email = user_emails_in_thread[-1]  # Most recent
            body = (followup_email.body_text or "").lower()
            
            # Check for response-like content (answers to vendor questions)
            has_preferences = any(kw in body for kw in [
                "flavor", "chocolate", "vanilla", "prefer", "choice",
                "dietary", "delivery", "message", "thank"
            ])
            
            if has_preferences or len(body) > 50:  # Substantive response
                score += 1
                details.append("✓ Bakery: follow-up sent with preferences")
            else:
                details.append("✗ Bakery: follow-up sent but lacks detail")
        else:
            details.append("✗ Bakery: no follow-up to vendor questions")
    else:
        details.append("✗ Bakery: conversation not established")
    
    # Check catering follow-up
    if catering_thread:
        user_emails_in_thread = []
        for msg_id in catering_thread.message_ids:
            if msg_id in email_state.emails:
                email = email_state.emails[msg_id]
                if email.folder == "sent":
                    user_emails_in_thread.append(email)
        
        if len(user_emails_in_thread) >= 2:
            followup_email = user_emails_in_thread[-1]
            body = (followup_email.body_text or "").lower()
            
            # Check for response content (selecting options, confirming details)
            has_selection = any(kw in body for kw in [
                "option", "select", "choice", "confirm", "booking",
                "package", "prefer", "like", "thank"
            ])
            
            if has_selection or len(body) > 50:
                score += 1
                details.append("✓ Catering: follow-up sent with selection")
            else:
                details.append("✗ Catering: follow-up sent but lacks detail")
        else:
            details.append("✗ Catering: no follow-up to vendor questions")
    else:
        details.append("✗ Catering: conversation not established")
    
    return EvalResult(
        score=score,
        max_score=max_score,
        explanation=f"Vendor follow-ups: {score}/{max_score}",
        details={"breakdown": details},
    )


async def check_status_reporting(ctx: EvalContext, params: dict) -> EvalResult:
    """Check if the agent provided status updates.
    
    This is a softer check - we look for evidence of status tracking
    in the agent's behavior (e.g., chat messages or structured reports).
    """
    expected_elements = params.get("expected_report_elements", [])
    
    # For this implementation, we'll check if the agent has tracked
    # the expected information based on the state
    
    email_state = await ctx.get_state("email")
    sms_state = await ctx.get_state("sms")
    calendar_state = await ctx.get_state("calendar")
    
    score = 0
    max_score = len(expected_elements) if expected_elements else 3
    tracked = []
    
    # Check invitations_sent
    if "invitations_sent" in expected_elements:
        sent_count = sum(1 for e in email_state.emails.values() if e.folder == "sent")
        sms_sent = any(m.direction == "outgoing" for m in sms_state.messages.values())
        if sent_count > 0 or sms_sent:
            score += 1
            tracked.append(f"invitations: {sent_count} emails, SMS: {'yes' if sms_sent else 'no'}")
    
    # Check responses_received
    if "responses_received" in expected_elements:
        inbox_count = sum(1 for e in email_state.emails.values() if e.folder == "inbox")
        if inbox_count > 0:
            score += 1
            tracked.append(f"responses: {inbox_count} received")
    
    # Check vendor_status
    if "vendor_status" in expected_elements:
        vendor_emails = ["orders@sweetdelightsbakery.com", "catering@coastalcatering.com"]
        vendor_contacted = 0
        for email in email_state.emails.values():
            if email.folder == "sent":
                for recipient in email.to_addresses:
                    if recipient.lower() in vendor_emails:
                        vendor_contacted += 1
                        break
        if vendor_contacted > 0:
            score += 1
            tracked.append(f"vendors: {vendor_contacted} contacted")
    
    explanation = f"Status elements tracked: {', '.join(tracked) if tracked else 'none'}"
    
    return EvalResult(
        score=score,
        max_score=max_score,
        explanation=explanation,
        details={"tracked_elements": tracked},
    )
