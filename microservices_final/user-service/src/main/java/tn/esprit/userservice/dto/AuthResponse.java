package tn.esprit.userservice.dto;

import tn.esprit.userservice.entity.RoleEnum;
import tn.esprit.userservice.entity.UserStatus;

public class AuthResponse {
    private String token;
    private String email;
    private String fullName;
    private RoleEnum role;
    private Long id;
    private boolean emailVerified;
    private UserStatus status;
    private String message;
    private boolean success;

    public AuthResponse() {}

    public AuthResponse(String token, String email, String fullName, RoleEnum role, Long id,
                        boolean emailVerified, UserStatus status, String message, boolean success) {
        this.token = token;
        this.email = email;
        this.fullName = fullName;
        this.role = role;
        this.id = id;
        this.emailVerified = emailVerified;
        this.status = status;
        this.message = message;
        this.success = success;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String token;
        private String email;
        private String fullName;
        private RoleEnum role;
        private Long id;
        private boolean emailVerified;
        private UserStatus status;
        private String message;
        private boolean success;

        public Builder token(String token) { this.token = token; return this; }
        public Builder email(String email) { this.email = email; return this; }
        public Builder fullName(String fullName) { this.fullName = fullName; return this; }
        public Builder role(RoleEnum role) { this.role = role; return this; }
        public Builder id(Long id) { this.id = id; return this; }
        public Builder emailVerified(boolean emailVerified) { this.emailVerified = emailVerified; return this; }
        public Builder status(UserStatus status) { this.status = status; return this; }
        public Builder message(String message) { this.message = message; return this; }
        public Builder success(boolean success) { this.success = success; return this; }

        public AuthResponse build() {
            return new AuthResponse(token, email, fullName, role, id, emailVerified, status, message, success);
        }
    }

    // Getters
    public String getToken() { return token; }
    public String getEmail() { return email; }
    public String getFullName() { return fullName; }
    public RoleEnum getRole() { return role; }
    public Long getId() { return id; }
    public boolean isEmailVerified() { return emailVerified; }
    public UserStatus getStatus() { return status; }
    public String getMessage() { return message; }
    public boolean isSuccess() { return success; }

    // Setters
    public void setToken(String token) { this.token = token; }
    public void setEmail(String email) { this.email = email; }
    public void setFullName(String fullName) { this.fullName = fullName; }
    public void setRole(RoleEnum role) { this.role = role; }
    public void setId(Long id) { this.id = id; }
    public void setEmailVerified(boolean emailVerified) { this.emailVerified = emailVerified; }
    public void setStatus(UserStatus status) { this.status = status; }
    public void setMessage(String message) { this.message = message; }
    public void setSuccess(boolean success) { this.success = success; }
}