pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

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

    }
}
