package tn.esprit.userservice.dto;

import tn.esprit.userservice.entity.RoleEnum;
import tn.esprit.userservice.entity.UserStatus;

import java.time.LocalDateTime;

public class UserResponse {
    private Long id;
    private String fullName;
    private String email;
    private String phoneNumber;
    private String address;
    private String city;
    private String postalCode;
    private String country;
    private RoleEnum role;
    private UserStatus status;
    private boolean emailVerified;
    private LocalDateTime lastLogin;
    private LocalDateTime createdAt;

    // Constructeur par défaut
    public UserResponse() {}

    // Constructeur avec tous les paramètres
    public UserResponse(Long id, String fullName, String email, String phoneNumber, String address,
                        String city, String postalCode, String country, RoleEnum role, UserStatus status,
                        boolean emailVerified, LocalDateTime lastLogin, LocalDateTime createdAt) {
        this.id = id;
        this.fullName = fullName;
        this.email = email;
        this.phoneNumber = phoneNumber;
        this.address = address;
        this.city = city;
        this.postalCode = postalCode;
        this.country = country;
        this.role = role;
        this.status = status;
        this.emailVerified = emailVerified;
        this.lastLogin = lastLogin;
        this.createdAt = createdAt;
    }

    // ========== BUILDER ==========
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private Long id;
        private String fullName;
        private String email;
        private String phoneNumber;
        private String address;
        private String city;
        private String postalCode;
        private String country;
        private RoleEnum role;
        private UserStatus status;
        private boolean emailVerified;
        private LocalDateTime lastLogin;
        private LocalDateTime createdAt;

        public Builder id(Long id) { this.id = id; return this; }
        public Builder fullName(String fullName) { this.fullName = fullName; return this; }
        public Builder email(String email) { this.email = email; return this; }
        public Builder phoneNumber(String phoneNumber) { this.phoneNumber = phoneNumber; return this; }
        public Builder address(String address) { this.address = address; return this; }
        public Builder city(String city) { this.city = city; return this; }
        public Builder postalCode(String postalCode) { this.postalCode = postalCode; return this; }
        public Builder country(String country) { this.country = country; return this; }
        public Builder role(RoleEnum role) { this.role = role; return this; }
        public Builder status(UserStatus status) { this.status = status; return this; }
        public Builder emailVerified(boolean emailVerified) { this.emailVerified = emailVerified; return this; }
        public Builder lastLogin(LocalDateTime lastLogin) { this.lastLogin = lastLogin; return this; }
        public Builder createdAt(LocalDateTime createdAt) { this.createdAt = createdAt; return this; }

        public UserResponse build() {
            return new UserResponse(id, fullName, email, phoneNumber, address, city, postalCode, country,
                    role, status, emailVerified, lastLogin, createdAt);
        }
    }

    // ========== GETTERS ==========
    public Long getId() { return id; }
    public String getFullName() { return fullName; }
    public String getEmail() { return email; }
    public String getPhoneNumber() { return phoneNumber; }
    public String getAddress() { return address; }
    public String getCity() { return city; }
    public String getPostalCode() { return postalCode; }
    public String getCountry() { return country; }
    public RoleEnum getRole() { return role; }
    public UserStatus getStatus() { return status; }
    public boolean isEmailVerified() { return emailVerified; }
    public LocalDateTime getLastLogin() { return lastLogin; }
    public LocalDateTime getCreatedAt() { return createdAt; }

    // ========== SETTERS ==========
    public void setId(Long id) { this.id = id; }
    public void setFullName(String fullName) { this.fullName = fullName; }
    public void setEmail(String email) { this.email = email; }
    public void setPhoneNumber(String phoneNumber) { this.phoneNumber = phoneNumber; }
    public void setAddress(String address) { this.address = address; }
    public void setCity(String city) { this.city = city; }
    public void setPostalCode(String postalCode) { this.postalCode = postalCode; }
    public void setCountry(String country) { this.country = country; }
    public void setRole(RoleEnum role) { this.role = role; }
    public void setStatus(UserStatus status) { this.status = status; }
    public void setEmailVerified(boolean emailVerified) { this.emailVerified = emailVerified; }
    public void setLastLogin(LocalDateTime lastLogin) { this.lastLogin = lastLogin; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}