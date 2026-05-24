package tn.esprit.userservice.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import tn.esprit.userservice.dto.*;
import tn.esprit.userservice.entity.User;
import tn.esprit.userservice.entity.UserStatus;
import tn.esprit.userservice.service.UserService;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserService userService;

    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(@Valid @RequestBody UserRequest request) {
        try {
            User user = userService.register(request);

            AuthResponse response = AuthResponse.builder()
                    .id(user.getId())
                    .email(user.getEmail())
                    .fullName(user.getFullName())
                    .role(user.getRole())
                    .emailVerified(user.isEmailVerified())
                    .status(user.getStatus())
                    .message("Registration successful. Please check your email to verify your account.")
                    .success(true)
                    .build();

            return ResponseEntity.status(HttpStatus.CREATED).body(response);
        } catch (RuntimeException e) {
            AuthResponse response = AuthResponse.builder()
                    .success(false)
                    .message(e.getMessage())
                    .build();
            return ResponseEntity.badRequest().body(response);
        }
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody AuthRequest request) {
        try {
            User user = userService.login(request.getEmail(), request.getPassword());

            // Générer token JWT (à implémenter)
            String jwtToken = "jwt-token-" + System.currentTimeMillis();

            AuthResponse response = AuthResponse.builder()
                    .token(jwtToken)
                    .id(user.getId())
                    .email(user.getEmail())
                    .fullName(user.getFullName())
                    .role(user.getRole())
                    .emailVerified(user.isEmailVerified())
                    .status(user.getStatus())
                    .message("Login successful")
                    .success(true)
                    .build();

            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            AuthResponse response = AuthResponse.builder()
                    .success(false)
                    .message(e.getMessage())
                    .build();
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(response);
        }
    }

    @GetMapping("/verify")
    public ResponseEntity<AuthResponse> verifyEmail(@RequestParam String token) {
        try {
            User user = userService.verifyEmail(token);

            AuthResponse response = AuthResponse.builder()
                    .id(user.getId())
                    .email(user.getEmail())
                    .fullName(user.getFullName())
                    .role(user.getRole())
                    .emailVerified(true)
                    .status(UserStatus.ACTIVE)
                    .message("Email verified successfully! Your account is now active.")
                    .success(true)
                    .build();

            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            AuthResponse response = AuthResponse.builder()
                    .success(false)
                    .message(e.getMessage())
                    .build();
            return ResponseEntity.badRequest().body(response);
        }
    }

    @PostMapping("/resend-verification")
    public ResponseEntity<AuthResponse> resendVerification(@Valid @RequestBody ResendVerificationRequest request) {
        try {
            userService.resendVerificationEmail(request.getEmail());

            AuthResponse response = AuthResponse.builder()
                    .success(true)
                    .message("Verification email resent successfully")
                    .build();

            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            AuthResponse response = AuthResponse.builder()
                    .success(false)
                    .message(e.getMessage())
                    .build();
            return ResponseEntity.badRequest().body(response);
        }
    }

    @PostMapping("/forgot-password")
    public ResponseEntity<AuthResponse> forgotPassword(@Valid @RequestBody ForgotPasswordRequest request) {
        userService.forgotPassword(request.getEmail());

        AuthResponse response = AuthResponse.builder()
                .success(true)
                .message("If your email is registered, you will receive a password reset link")
                .build();

        return ResponseEntity.ok(response);
    }

    @PostMapping("/reset-password")
    public ResponseEntity<AuthResponse> resetPassword(@Valid @RequestBody ResetPasswordRequest request) {
        if (!request.getNewPassword().equals(request.getConfirmPassword())) {
            AuthResponse response = AuthResponse.builder()
                    .success(false)
                    .message("Passwords do not match")
                    .build();
            return ResponseEntity.badRequest().body(response);
        }

        try {
            userService.resetPassword(request.getToken(), request.getNewPassword());

            AuthResponse response = AuthResponse.builder()
                    .success(true)
                    .message("Password reset successfully")
                    .build();

            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            AuthResponse response = AuthResponse.builder()
                    .success(false)
                    .message(e.getMessage())
                    .build();
            return ResponseEntity.badRequest().body(response);
        }
    }

    @GetMapping("/verification-status/{email}")
    public ResponseEntity<AuthResponse> checkVerificationStatus(@PathVariable String email) {
        try {
            boolean isVerified = userService.isEmailVerified(email);

            AuthResponse response = AuthResponse.builder()
                    .email(email)
                    .emailVerified(isVerified)
                    .success(true)
                    .message(isVerified ? "Email is verified" : "Email is not verified")
                    .build();

            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            AuthResponse response = AuthResponse.builder()
                    .success(false)
                    .message(e.getMessage())
                    .build();
            return ResponseEntity.badRequest().body(response);
        }
    }
}
