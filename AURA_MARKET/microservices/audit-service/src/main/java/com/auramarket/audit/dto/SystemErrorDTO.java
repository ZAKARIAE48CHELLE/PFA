package com.auramarket.audit.dto;

public class SystemErrorDTO {
    private String service;
    private String errorType;
    private String message;
    private String stackTrace;
    private String negociationId;
    private String userId;
    private String produitId;
    private String agentName;
    private String severity;
    private Long durationMs;
    private String payload;
    private String endpoint;

    public SystemErrorDTO() {}

    public String getService() { return service; }
    public void setService(String service) { this.service = service; }

    public String getErrorType() { return errorType; }
    public void setErrorType(String errorType) { this.errorType = errorType; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public String getStackTrace() { return stackTrace; }
    public void setStackTrace(String stackTrace) { this.stackTrace = stackTrace; }

    public String getNegociationId() { return negociationId; }
    public void setNegociationId(String negociationId) { this.negociationId = negociationId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getProduitId() { return produitId; }
    public void setProduitId(String produitId) { this.produitId = produitId; }

    public String getAgentName() { return agentName; }
    public void setAgentName(String agentName) { this.agentName = agentName; }

    public String getSeverity() { return severity; }
    public void setSeverity(String severity) { this.severity = severity; }

    public Long getDurationMs() { return durationMs; }
    public void setDurationMs(Long durationMs) { this.durationMs = durationMs; }

    public String getPayload() { return payload; }
    public void setPayload(String payload) { this.payload = payload; }

    public String getEndpoint() { return endpoint; }
    public void setEndpoint(String endpoint) { this.endpoint = endpoint; }
}
