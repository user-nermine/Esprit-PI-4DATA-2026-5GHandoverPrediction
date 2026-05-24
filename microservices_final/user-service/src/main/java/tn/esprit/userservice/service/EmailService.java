package tn.esprit.userservice.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import tn.esprit.userservice.entity.User;

@Service
@RequiredArgsConstructor
@Slf4j
public class EmailService {

    private final JavaMailSender mailSender;

    @Value("${spring.mail.username}")
    private String fromEmail;

    @Value("${app.backend-url:http://localhost:8081}")
    private String backendUrl;

    public void sendVerificationEmail(User user, String token) {
        String verificationUrl = backendUrl + "/api/auth/verify?token=" + token;

        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(fromEmail);
        message.setTo(user.getEmail());
        message.setSubject("Vérification de votre compte");
        message.setText("Bonjour " + user.getFullName() + ",\n\n" +
                "Cliquez sur ce lien pour vérifier votre compte :\n" +
                verificationUrl + "\n\n" +
                "Ce lien expire dans 24 heures.\n\n" +
                "Cordialement.");

        try {
            mailSender.send(message);
            log.info("Email envoyé à: {}", user.getEmail());
        } catch (Exception e) {
            log.error("Erreur envoi email: {}", e.getMessage());
        }
    }

    public void sendWelcomeEmail(User user) {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(fromEmail);
        message.setTo(user.getEmail());
        message.setSubject("Bienvenue !");
        message.setText("Bonjour " + user.getFullName() + ",\n\n" +
                "Votre compte a été activé avec succès !\n" +
                "Cordialement.");

        try {
            mailSender.send(message);
            log.info("Email de bienvenue envoyé à: {}", user.getEmail());
        } catch (Exception e) {
            log.error("Erreur envoi email: {}", e.getMessage());
        }
    }

    public void sendPasswordResetEmail(User user, String resetToken) {
        String resetUrl = backendUrl + "/api/auth/reset-password?token=" + resetToken;

        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(fromEmail);
        message.setTo(user.getEmail());
        message.setSubject("Réinitialisation mot de passe");
        message.setText("Bonjour " + user.getFullName() + ",\n\n" +
                "Cliquez sur ce lien pour réinitialiser votre mot de passe :\n" +
                resetUrl + "\n\n" +
                "Ce lien expire dans 1 heure.\n\n" +
                "Cordialement.");

        try {
            mailSender.send(message);
            log.info("Email de réinitialisation envoyé à: {}", user.getEmail());
        } catch (Exception e) {
            log.error("Erreur envoi email: {}", e.getMessage());
        }
    }
}