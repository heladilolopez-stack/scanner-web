pipeline {
    agent any

    stages {

        stage('Hola Jenkins') {
            steps {
                echo 'Jenkins está funcionando correctamente'
            }
        }

        stage('Verificar Docker') {
            steps {
                sh 'docker --version'
                sh 'docker compose version'
            }
        }

        stage('Build Docker') {
            steps {
                sh 'docker build -t scanner-web:latest .'
            }
        }

    }
}
