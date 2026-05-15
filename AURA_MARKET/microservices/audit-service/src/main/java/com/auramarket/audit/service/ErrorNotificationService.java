package com.auramarket.audit.service;

import com.auramarket.audit.entity.SystemError;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

@Service
public class ErrorNotificationService {

    @Autowired(required = false)
    private SimpMessagingTemplate messagingTemplate;

    public void notifySuperviseur(SystemError error) {
        if (messagingTemplate != null && error != null) {
            String sev = error.getSeverity() != null ? error.getSeverity().toUpperCase() : "MEDIUM";
            if ("CRITICAL".equals(sev) || "HIGH".equals(sev)) {
                try {
                    messagingTemplate.convertAndSend("/topic/errors", error);
                    System.out.println("[WS PUSH] Broadcaster pushed critical failure to supervisor channel.");
                } catch (Exception e) {
                    System.err.println("[WS PUSH ERROR] " + e.getMessage());
                }
            }
        }
    }
}
