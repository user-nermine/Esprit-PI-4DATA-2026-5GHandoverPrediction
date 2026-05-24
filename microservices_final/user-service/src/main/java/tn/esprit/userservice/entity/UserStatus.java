package tn.esprit.userservice.entity;

public enum UserStatus {
    ACTIVE,
    PENDING_VERIFICATION,  // NOUVEAU : en attente de vérification email
    SUSPENDED
}