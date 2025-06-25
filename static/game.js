// static/game.js

console.log('Game.js loaded successfully');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Socket.IO connection...');
    
    // Force WebSocket transport for better performance on Render
    const socket = io({ transports: ['websocket'] });
    console.log('Socket.IO connection created');
    
    let myUsername = null;

    // --- DOM Elements ---
    const log = document.getElementById('log');
    const playerList = document.getElementById('player-list');
    const turnIndicator = document.getElementById('turn-indicator');
    const myRole = document.getElementById('my-role');
    const myLocation = document.getElementById('my-location');
    
    const loginForm = document.getElementById('login-form');
    const gameForms = document.getElementById('game-forms');
    const askForm = document.getElementById('ask-form');
    const answerForm = document.getElementById('answer-form');
    
    const usernameInput = document.getElementById('username');
    const joinBtn = document.getElementById('join-btn');
    const startGameBtn = document.getElementById('start-game-btn');
    
    const questionInput = document.getElementById('question-input');
    const targetPlayerSelect = document.getElementById('target-player-select');
    const askBtn = document.getElementById('ask-btn');
    const answerInput = document.getElementById('answer-input');
    const answerBtn = document.getElementById('answer-btn');

    console.log('DOM elements found:', {
        log: !!log,
        playerList: !!playerList,
        loginForm: !!loginForm,
        gameForms: !!gameForms
    });

    // --- Event Listeners ---
    joinBtn.addEventListener('click', () => {
        console.log('Join button clicked');
        myUsername = usernameInput.value.trim();
        if (myUsername) {
            console.log('Joining with username:', myUsername);
            socket.emit('join', { username: myUsername });
            loginForm.classList.add('hidden');
            gameForms.classList.remove('hidden');
        }
    });

    startGameBtn.addEventListener('click', () => {
        console.log('Start game button clicked');
        socket.emit('start_game');
    });

    askBtn.addEventListener('click', () => {
        const question = questionInput.value.trim();
        const target = targetPlayerSelect.value;
        if (question && target) {
            console.log('Asking question:', question, 'to:', target);
            socket.emit('ask_question', { question, target });
            questionInput.value = '';
        }
    });
    
    answerBtn.addEventListener('click', () => {
        const answer = answerInput.value.trim();
        if (answer) {
            console.log('Submitting answer:', answer);
            socket.emit('submit_answer', { answer });
            answerInput.value = '';
        }
    });

    // --- Socket.IO Handlers ---
    socket.on('connect', () => {
        console.log('Connected to server');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });

    socket.on('connect_error', (error) => {
        console.error('Connection error:', error);
    });

    socket.on('game_started', (data) => {
        console.log('Game started with data:', data);
        myRole.textContent = data.is_outsider ? "You are the Outsider!" : "You are an Insider.";
        myLocation.textContent = `Location: ${data.location}`;
        startGameBtn.classList.add('hidden');
    });
    
    socket.on('game_over', (data) => {
        console.log('Game over:', data);
        
        // Hide game forms
        askForm.classList.add('hidden');
        answerForm.classList.add('hidden');
        
        // Show game over message
        let gameOverMessage = '';
        if (data.win_reason === 'outsider_guess') {
            gameOverMessage = `🎉 ${data.winner} correctly guessed the location! The location was ${data.actual_location}. The Outsider wins!`;
        }
        
        const gameOverEntry = document.createElement('p');
        gameOverEntry.style.fontWeight = 'bold';
        gameOverEntry.style.color = '#d32f2f';
        gameOverEntry.style.fontSize = '16px';
        gameOverEntry.textContent = gameOverMessage;
        log.appendChild(gameOverEntry);
        log.scrollTop = log.scrollHeight;
        
        // Update turn indicator
        turnIndicator.textContent = 'Game Over!';
        turnIndicator.style.color = '#d32f2f';
        
        // Show restart option
        const restartBtn = document.createElement('button');
        restartBtn.textContent = 'Play Again';
        restartBtn.style.marginTop = '10px';
        restartBtn.addEventListener('click', () => {
            location.reload();
        });
        document.getElementById('input-area').appendChild(restartBtn);
    });

    socket.on('game_update', (data) => {
        console.log('Game update received:', data);
        
        // Check if game is over
        if (data.game_over) {
            // Hide game forms
            askForm.classList.add('hidden');
            answerForm.classList.add('hidden');
            
            // Show game over message
            let gameOverMessage = '';
            if (data.win_reason === 'outsider_guess') {
                gameOverMessage = `🎉 ${data.winner} correctly guessed the location! The location was ${data.actual_location}. The Outsider wins!`;
            }
            
            const gameOverEntry = document.createElement('p');
            gameOverEntry.style.fontWeight = 'bold';
            gameOverEntry.style.color = '#d32f2f';
            gameOverEntry.style.fontSize = '16px';
            gameOverEntry.textContent = gameOverMessage;
            log.appendChild(gameOverEntry);
            log.scrollTop = log.scrollHeight;
            
            // Update turn indicator
            turnIndicator.textContent = 'Game Over!';
            turnIndicator.style.color = '#d32f2f';
            
            // Show restart option
            const restartBtn = document.createElement('button');
            restartBtn.textContent = 'Play Again';
            restartBtn.style.marginTop = '10px';
            restartBtn.addEventListener('click', () => {
                location.reload();
            });
            document.getElementById('input-area').appendChild(restartBtn);
            
            return; // Don't process other updates
        }
        
        // Update player list
        if (data.players) {
            playerList.innerHTML = '';
            targetPlayerSelect.innerHTML = '';
            
            data.players.forEach(player => {
                const li = document.createElement('li');
                li.textContent = player;
                playerList.appendChild(li);

                // Add to dropdown for asking questions, but don't let players ask themselves
                if (player !== myUsername) {
                    const option = document.createElement('option');
                    option.value = player;
                    option.textContent = player;
                    targetPlayerSelect.appendChild(option);
                }
            });
        }
        
        // Add new log entry
        if (data.log) {
            const entry = document.createElement('p');
            entry.textContent = data.log;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight; // Auto-scroll
        }
        
        // Update turn indicator and forms
        if (data.current_turn) {
            const isMyTurn = data.current_turn === myUsername;
            
            if (isMyTurn) {
                turnIndicator.textContent = `It's your turn!`;
                if (data.mode === 'answering') {
                    askForm.classList.add('hidden');
                    answerForm.classList.remove('hidden');
                } else { // Default to asking
                    askForm.classList.remove('hidden');
                    answerForm.classList.add('hidden');
                }
            } else {
                turnIndicator.textContent = `It's ${data.current_turn}'s turn.`;
                askForm.classList.add('hidden');
                answerForm.classList.add('hidden');
            }
        }
    });

    console.log('Event listeners and Socket.IO handlers set up successfully');
});