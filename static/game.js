// static/game.js

console.log('Game.js loaded successfully');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing...');

    // --- Configuration ---
    const TYPING_TIMEOUT_MS = 2000;

    // --- DOM Elements (Cached) ---
    const DOM = {
        log: document.getElementById('log'),
        playerList: document.getElementById('player-list'),
        turnIndicator: document.getElementById('turn-indicator'),
        myRole: document.getElementById('my-role'),
        myLocation: document.getElementById('my-location'),
        questionCounter: document.getElementById('question-counter'),
        questionCount: document.getElementById('question-count'),
        questionsUntilVote: document.getElementById('questions-until-vote'),
        loginForm: document.getElementById('login-form'),
        gameForms: document.getElementById('game-forms'),
        askForm: document.getElementById('ask-form'),
        answerForm: document.getElementById('answer-form'),
        voteForm: document.getElementById('vote-form'),
        voteOptions: document.getElementById('vote-options'),
        submitVoteBtn: document.getElementById('submit-vote-btn'),
        usernameInput: document.getElementById('username'),
        joinBtn: document.getElementById('join-btn'),
        startGameBtn: document.getElementById('start-game-btn'),
        manualResetBtn: document.getElementById('manual-reset-btn'),
        questionInput: document.getElementById('question-input'),
        targetPlayerSelect: document.getElementById('target-player-select'),
        askBtn: document.getElementById('ask-btn'),
        answerInput: document.getElementById('answer-input'),
        answerBtn: document.getElementById('answer-btn'),
        winCounter: document.getElementById('win-counter'),
        humanWinsDisplay: document.querySelector('.human-wins'),
        aiWinsDisplay: document.querySelector('.ai-wins')
    };

    // --- Game State ---
    let state = {
        myUsername: null,
        selectedVoteTarget: null,
        isSpectator: false,
        isTyping: false,
        typingTimeout: null,
        socket: null,
        roomJoined: false
    };

    // --- Helper Functions (UI & Logic) ---

    /**
     * Adds a styled message to the game log.
     * @param {string} message The text to display.
     * @param {'normal'|'system'|'error'|'success'|'question'|'answer'|'vote'|'info'} type The message style.
     */
    function addMessageToLog(message, type = 'normal') {
        const entry = document.createElement('p');
        entry.innerHTML = message; // Use innerHTML to support bold tags etc.
        entry.className = `log-entry log-${type}`;
        DOM.log.appendChild(entry);
        DOM.log.scrollTop = DOM.log.scrollHeight;
    }

    /**
     * Updates the turn indicator text and color.
     * @param {string} text The message to display.
     * @param {string} color A valid CSS color.
     */
    function updateTurnIndicator(text, color = '#666') {
        DOM.turnIndicator.textContent = text;
        DOM.turnIndicator.style.color = color;
    }

    /**
     * Updates the player list and the target player dropdown.
     * @param {string[]} players An array of player usernames.
     */
    function updatePlayerList(players) {
        DOM.playerList.innerHTML = '';
        DOM.targetPlayerSelect.innerHTML = '';
        players.forEach(player => {
            const li = document.createElement('li');
            li.textContent = player;
            DOM.playerList.appendChild(li);

            if (player !== state.myUsername && !state.isSpectator) {
                const option = document.createElement('option');
                option.value = player;
                option.textContent = player;
                DOM.targetPlayerSelect.appendChild(option);
            }
        });
    }

    /**
     * Updates the question counter and the "vote now" button.
     * @param {object} data The update data from the server.
     */
    function updateQuestionCounter(data) {
        if (data.question_count !== undefined) {
            DOM.questionCount.textContent = data.question_count;
        }
        if (data.questions_until_vote !== undefined) {
            const canVote = data.questions_until_vote === 0;
            const canRequestVote = canVote && !state.isSpectator;

            DOM.questionsUntilVote.textContent = canVote
                ? (state.isSpectator ? 'Can vote now! (Spectating)' : 'Can vote now!')
                : `${data.questions_until_vote} until vote`;

            DOM.questionsUntilVote.style.cursor = canRequestVote ? 'pointer' : 'default';
            DOM.questionsUntilVote.style.color = canRequestVote ? '#ff9800' : '#666';
            DOM.questionsUntilVote.style.fontWeight = canRequestVote ? 'bold' : 'normal';
            DOM.questionsUntilVote.title = canRequestVote ? 'Click to request a vote!' : '';

            if (canRequestVote) {
                DOM.questionsUntilVote.onclick = () => {
                    state.socket.emit('request_vote', {});
                    DOM.questionsUntilVote.textContent = 'Vote Requested...';
                    DOM.questionsUntilVote.style.cursor = 'default';
                    DOM.questionsUntilVote.onclick = null;
                };
            } else {
                DOM.questionsUntilVote.onclick = null;
            }
        }
    }

    /**
     * Shows or hides the main game forms (ask, answer, vote).
     * @param {{ask: boolean, answer: boolean, vote: boolean}} visibility
     */
    function setFormVisibility({ ask = false, answer = false, vote = false }) {
        console.log('=== SET_FORM_VISIBILITY CALLED ===');
        console.log('Parameters:', { ask, answer, vote });
        console.log('Before changes:');
        console.log('- Ask form hidden:', DOM.askForm.classList.contains('hidden'));
        console.log('- Answer form hidden:', DOM.answerForm.classList.contains('hidden'));
        console.log('- Vote form hidden:', DOM.voteForm.classList.contains('hidden'));
        
        DOM.askForm.classList.toggle('hidden', !ask);
        DOM.answerForm.classList.toggle('hidden', !answer);
        DOM.voteForm.classList.toggle('hidden', !vote);

        // Enable/disable inputs to prevent interaction with hidden forms
        [DOM.questionInput, DOM.targetPlayerSelect, DOM.askBtn].forEach(el => el.disabled = !ask);
        [DOM.answerInput, DOM.answerBtn].forEach(el => el.disabled = !answer);

        console.log('After changes:');
        console.log('- Ask form hidden:', DOM.askForm.classList.contains('hidden'));
        console.log('- Answer form hidden:', DOM.answerForm.classList.contains('hidden'));
        console.log('- Vote form hidden:', DOM.voteForm.classList.contains('hidden'));
        console.log('- Question input disabled:', DOM.questionInput.disabled);
        console.log('- Answer input disabled:', DOM.answerInput.disabled);

        if (ask) DOM.questionInput.focus();
        if (answer) DOM.answerInput.focus();
    }

    /**
     * Resets the entire UI to its initial, pre-game state.
     */
    function resetUIForNewGame() {
        console.log('Resetting UI to initial state.');
        DOM.myRole.textContent = 'Waiting...';
        DOM.myLocation.textContent = 'Location: ???';
        DOM.loginForm.classList.remove('hidden');
        DOM.gameForms.classList.add('hidden');
        DOM.playerList.innerHTML = '';
        DOM.questionCounter.classList.add('hidden');
        updateTurnIndicator('Game reset! Enter your name to join a new game.', '#2196f3');
        DOM.usernameInput.value = '';
        DOM.usernameInput.focus();

        state.isSpectator = false;
        state.myUsername = null;

        addMessageToLog('<strong>Game has been reset!</strong>', 'system');
        addMessageToLog('Enter your name above to join a new game!', 'info');
    }

    // --- Typing Indicator Functions ---
    function startTyping() {
        if (!state.isTyping) {
            state.isTyping = true;
            state.socket.emit('typing_start', { username: state.myUsername });
        }
        clearTimeout(state.typingTimeout);
        state.typingTimeout = setTimeout(stopTyping, TYPING_TIMEOUT_MS);
    }

    function stopTyping() {
        if (state.isTyping) {
            state.isTyping = false;
            state.socket.emit('typing_stop', { username: state.myUsername });
        }
        clearTimeout(state.typingTimeout);
        state.typingTimeout = null;
    }

    // --- Event Listeners (DOM) ---
    DOM.joinBtn.addEventListener('click', () => {
        const username = DOM.usernameInput.value.trim();
        if (username) {
            state.myUsername = username;
            state.socket.emit('join', { username: state.myUsername });
            DOM.loginForm.classList.add('hidden');
        }
    });

    DOM.startGameBtn.addEventListener('click', () => {
        console.log('=== START GAME BUTTON CLICKED ===');
        console.log('Button disabled state:', DOM.startGameBtn.disabled);
        console.log('Button hidden state:', DOM.startGameBtn.classList.contains('hidden'));
        console.log('Current time:', Date.now());
        console.log('Room joining status:');
        console.log('- Has joined room:', state.socket.connected);
        console.log('- Room joined event received:', state.roomJoined || false);
        console.log('- Socket connected:', state.socket.connected);
        console.log('- Is spectator:', state.isSpectator);
        
        if (DOM.startGameBtn.disabled) {
            console.log('Start button is disabled, ignoring click');
            return;
        }
        
        if (DOM.startGameBtn.classList.contains('hidden')) {
            console.log('Start button is hidden, ignoring click');
            return;
        }
        
        console.log('Emitting start_game event...');
        state.socket.emit('start_game', {});
        DOM.startGameBtn.disabled = true;
        console.log('Start button disabled after click');
    });

    DOM.manualResetBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset the game? This will clear all data.')) {
            state.socket.emit('manual_reset');
        }
    });

    DOM.askBtn.addEventListener('click', () => {
        if (state.isSpectator) return;
        const question = DOM.questionInput.value.trim();
        const target = DOM.targetPlayerSelect.value;
        if (question && target) {
            state.socket.emit('ask_question', { question, target });
            DOM.questionInput.value = '';
            stopTyping();
            // Don't hide the form immediately - let the server's turn_update event control visibility
            // setFormVisibility({ ask: false });
            updateTurnIndicator(`Question sent to ${target}!`, '#4caf50');
        }
    });

    DOM.answerBtn.addEventListener('click', () => {
        if (state.isSpectator) return;
        const answer = DOM.answerInput.value.trim();
        if (answer) {
            state.socket.emit('submit_answer', { answer });
            DOM.answerInput.value = '';
            stopTyping();
            // Don't hide the form immediately - let the server's turn_update event control visibility
            // setFormVisibility({ answer: false });
            updateTurnIndicator('Answer sent!', '#4caf50');
        }
    });

    DOM.submitVoteBtn.addEventListener('click', () => {
        if (state.isSpectator || !state.selectedVoteTarget) return;
        state.socket.emit('submit_vote', { voted_for_sid: state.selectedVoteTarget });
        DOM.submitVoteBtn.disabled = true;
        DOM.submitVoteBtn.textContent = 'Vote Submitted';
    });

    // Typing listeners
    DOM.questionInput.addEventListener('input', startTyping);
    DOM.answerInput.addEventListener('input', startTyping);
    DOM.questionInput.addEventListener('blur', stopTyping);
    DOM.answerInput.addEventListener('blur', stopTyping);


    // --- Socket.IO Initialization & Handlers ---
    function initializeSocket() {
        state.socket = io({ transports: ['websocket', 'polling'] });

        // Welcome messages
    addMessageToLog('👋 Welcome to The Outsider!', 'system');
        addMessageToLog('The AI is always the Outsider - humans must work together to identify and vote it out!', 'info');
    
        // --- Core Connection Handlers ---
        state.socket.on('connect', () => {
        console.log('Connected to server!');
            addMessageToLog('Connected to game server!', 'success');
            state.socket.emit('join_room', { room: 'main' });
        });

        state.socket.on('room_joined', (data) => {
            console.log('=== ROOM_JOINED EVENT RECEIVED ===');
            console.log('Room joined:', data);
            addMessageToLog(`Joined room: ${data.room}`, 'success');
            state.roomJoined = true;
        });

        state.socket.on('disconnect', () => {
            addMessageToLog('Disconnected. Trying to reconnect...', 'error');
        });

        state.socket.on('connect_error', (error) => {
            addMessageToLog(`Connection error: ${error.message}`, 'error');
        });

        // Debug: Listen for all events
        state.socket.onAny((eventName, ...args) => {
            console.log(`=== RECEIVED EVENT: ${eventName} ===`);
            console.log('Event args:', args);
            
            // Special debugging for turn_update events
            if (eventName === 'turn_update') {
                console.log('=== TURN_UPDATE EVENT DETECTED BY ONANY ===');
                console.log('Turn update data:', args[0]);
                console.log('Current time:', Date.now());
            }
            
            // Special debugging for game_started events
            if (eventName === 'game_started') {
                console.log('=== GAME_STARTED EVENT DETECTED BY ONANY ===');
                console.log('Game started data:', args[0]);
                console.log('Current time:', Date.now());
            }
        });

        // --- Game State Handlers ---
        state.socket.on('game_update', (data) => {
            console.log('Game Update:', data);
            if (data.players) updatePlayerList(data.players);

            if (data.can_start_game !== undefined && !state.isSpectator) {
                DOM.startGameBtn.classList.toggle('hidden', !data.can_start_game);
                DOM.startGameBtn.disabled = !data.can_start_game;
            }
            if (data.log) {
                const logType = data.error ? 'error' : 'system';
                addMessageToLog(data.log, logType);
            }
        });

        console.log('Registering game_started event handler...');
        state.socket.on('game_started', (data) => {
            console.log('=== GAME_STARTED EVENT RECEIVED ===');
            console.log('Game Started:', data);
            console.log('Data type:', typeof data);
            console.log('Data keys:', Object.keys(data));
            console.log('Location:', data.location);
            console.log('Players:', data.players);
            console.log('Current UI state:');
            console.log('- Login form hidden:', DOM.loginForm.classList.contains('hidden'));
            console.log('- Game forms hidden:', DOM.gameForms.classList.contains('hidden'));
            console.log('- Start button hidden:', DOM.startGameBtn.classList.contains('hidden'));
            console.log('- Start button disabled:', DOM.startGameBtn.disabled);
            console.log('- myUsername:', state.myUsername);
            
            state.isSpectator = false;
            DOM.myRole.textContent = `You are: ${state.myUsername}`;
            DOM.myLocation.textContent = `Location: ${data.location}`;
            DOM.startGameBtn.classList.add('hidden');
            console.log('Start button hidden after game started');
            DOM.questionCounter.classList.remove('hidden');
            updateQuestionCounter({ question_count: 0, questions_until_vote: 5 });
            setFormVisibility({}); // Hide all forms
            updateTurnIndicator('Waiting for first question...');
            updatePlayerList(data.players); // Ensure player list is updated
            DOM.gameForms.classList.remove('hidden');
            console.log('Game forms shown after game started');
        });
        console.log('game_started event handler registered');

        state.socket.on('spectator_mode', (data) => {
            console.log('Spectator Mode:', data);
            state.isSpectator = true;
            DOM.myRole.textContent = "You are a Spectator";
            DOM.myLocation.textContent = "Location: ???";
            DOM.startGameBtn.classList.add('hidden');
            DOM.questionCounter.classList.remove('hidden');
            DOM.gameForms.classList.remove('hidden');
            setFormVisibility({}); // Hide all forms
            updateTurnIndicator("👁️ Spectating - Watch the game!", '#666');
            if (data.question_count !== undefined) updateQuestionCounter(data);
            addMessageToLog(data.message, 'system');
        });

        state.socket.on('game_reset', (data) => {
            // Display the reset message from the server before clearing the UI
            if (data.message) {
                addMessageToLog(data.message, 'system');
            }
            
            resetUIForNewGame();
            // Win counter is now persistent across all resets (including manual resets)
            // No longer reset win counter for any type of reset
        });

        state.socket.on('game_ended', (data) => {
            console.log('Game Ended:', data);
            setFormVisibility({});
            addMessageToLog(data.message, data.winner === 'humans' ? 'success' : 'error');
            updateTurnIndicator(`Game Over! ${data.winner === 'humans' ? 'Humans Win!' : 'AI Wins!'}`, data.winner === 'humans' ? '#4caf50' : '#d32f2f');
        });

        // --- Turn & Action Handlers ---
        state.socket.on('turn_update', (data) => {
            console.log('=== TURN_UPDATE EVENT RECEIVED ===');
            console.log('Turn Update:', data);
        console.log('Data type:', typeof data);
        console.log('Data keys:', Object.keys(data));
            console.log('My username:', state.myUsername);
        console.log('Is my turn to ask:', data.is_my_turn_to_ask);
        console.log('Is my turn to answer:', data.is_my_turn_to_answer);
        console.log('Can ask:', data.can_ask);
        console.log('Can answer:', data.can_answer);
        console.log('Current form states:');
            console.log('- Ask form hidden:', DOM.askForm.classList.contains('hidden'));
            console.log('- Answer form hidden:', DOM.answerForm.classList.contains('hidden'));
            console.log('- Question input disabled:', DOM.questionInput.disabled);
            console.log('- Answer input disabled:', DOM.answerInput.disabled);
            
            if (state.isSpectator) {
                updateTurnIndicator(`${data.current_asker} is asking ${data.current_target || '...'}`, '#666');
                return;
            }

            setFormVisibility({ ask: data.can_ask, answer: data.can_answer });

            if (data.is_my_turn_to_ask) {
                updateTurnIndicator("It's your turn to ask a question!", '#4caf50');
            } else if (data.is_my_turn_to_answer) {
                updateTurnIndicator(`${data.current_asker} is asking you a question!`, '#ff9800');
        } else {
                updateTurnIndicator(`${data.current_asker} is asking ${data.current_target || '...'}`, '#666');
            }
        });

        state.socket.on('spectator_turn_update', (data) => {
            console.log('Spectator Turn Update:', data);
        
        // Only update turn indicator for spectators (don't change forms)
        if (data.current_asker) {
            if (data.current_target) {
                    updateTurnIndicator(`${data.current_asker} is asking ${data.current_target} a question.`, '#666');
            } else {
                    updateTurnIndicator(`${data.current_asker} is thinking of a question...`, '#666');
                }
            }
        });

        state.socket.on('question_asked', (data) => {
            addMessageToLog(`<strong>${data.asker}</strong> asks <strong>${data.target}</strong>: ${data.question}`, 'question');
        });
        
        state.socket.on('ai_question', (data) => {
        console.log('AI question:', data);
        
        // Get AI player name from the target SID
        const aiPlayer = data.target; // This should be the AI's SID
        const aiName = aiPlayer.replace('ai_', ''); // Extract name from SID like "ai_Sam"
        
        // Add AI question to chat
            addMessageToLog(`<strong>${aiName}</strong> asks: ${data.question}`, 'question');
        
        // Update turn indicator immediately
            if (data.target_sid === state.myUsername) {
                updateTurnIndicator(`${aiName} is asking you a question!`, '#ff9800');
                setFormVisibility({ answer: true });
        } else {
                updateTurnIndicator(`${aiName} is asking ${data.target} a question.`, '#666');
                setFormVisibility({});
            }
        });
        
        state.socket.on('answer_given', (data) => {
            addMessageToLog(`<strong>${data.target}</strong> answers: ${data.answer}`, 'answer');
        });
        
        state.socket.on('ai_answer', (data) => {
        console.log('AI answer:', data);
        
        // Add AI answer to chat
            addMessageToLog(`<strong>${data.target}</strong> answers: ${data.answer}`, 'answer');
        
        // Clear answer form and disable inputs (in case this player was answering)
            setFormVisibility({});
            updateTurnIndicator('Processing answer...', '#666');
        });
        
        state.socket.on('location_guess_made', (data) => {
        console.log('Location guess made:', data);
        
        // Add anonymous location guess to chat with appropriate emoji
        const emoji = data.is_correct ? "🎯" : "❌";
            addMessageToLog(`<strong>${emoji} ${data.message}</strong>`, data.is_correct ? 'success' : 'error');
        });
        
        state.socket.on('question_count_update', updateQuestionCounter);

        // --- Voting Handlers ---
        state.socket.on('voting_started', (data) => {
            console.log('Voting Started:', data);
            setFormVisibility({ vote: true });
            updateTurnIndicator('🗳️ Voting Time! Who is the AI?', '#ff9800');
            addMessageToLog('🗳️ Voting has begun!', 'vote');

            DOM.voteOptions.innerHTML = '';
            state.selectedVoteTarget = null;
            DOM.submitVoteBtn.disabled = true;
            DOM.submitVoteBtn.textContent = 'Submit Vote';

            const createVoteOption = (text, sid) => {
                    const option = document.createElement('div');
                    option.className = 'vote-option';
                option.textContent = text;
                option.dataset.sid = sid;
                    option.addEventListener('click', () => {
                    document.querySelectorAll('.vote-option.selected').forEach(opt => opt.classList.remove('selected'));
                        option.classList.add('selected');
                    state.selectedVoteTarget = sid;
                    DOM.submitVoteBtn.disabled = false;
                    DOM.submitVoteBtn.textContent = `Vote for ${text}`;
                });
                return option;
            };

            data.players.forEach(player => {
                if (player.username !== state.myUsername) {
                    DOM.voteOptions.appendChild(createVoteOption(player.username, player.sid));
                }
            });
            DOM.voteOptions.appendChild(createVoteOption('Pass', 'pass'));
        });

        state.socket.on('voting_results', (data) => {
            addMessageToLog(data.message, 'vote');
        if (data.all_passed) {
                setFormVisibility({}); // Hide vote form, next turn_update will show correct form
                updateTurnIndicator('🤝 Everyone passed! Game continues...', '#4caf50');
            }
        });

        state.socket.on('vote_status_update', (data) => {
            console.log('Vote Status Update:', data);
            addMessageToLog(`📊 ${data.message}`, 'system');
            
            // Update turn indicator with voting progress
            if (data.total_votes < data.total_players) {
                updateTurnIndicator(`🗳️ Voting in progress... ${data.total_votes}/${data.total_players} votes`, '#ff9800');
            } else {
                updateTurnIndicator('🗳️ All votes received! Processing results...', '#4caf50');
            }
        });

        // --- Miscellaneous Handlers ---
        state.socket.on('win_counter_update', (data) => {
            DOM.humanWinsDisplay.textContent = data.human_wins;
            DOM.aiWinsDisplay.textContent = data.ai_wins;
        });

        state.socket.on('username_taken', (data) => {
            addMessageToLog(data.message, 'error');
            DOM.loginForm.classList.remove('hidden');
            DOM.gameForms.classList.add('hidden');
            DOM.usernameInput.value = '';
            DOM.usernameInput.focus();
        });
        
        state.socket.on('typing_start', (data) => {
            if (data.username !== state.myUsername) {
                const typingId = `typing-${data.username}`;
                if (!document.getElementById(typingId)) {
                    const entry = document.createElement('p');
                    entry.textContent = `${data.username} is typing...`;
                    entry.className = 'log-entry log-typing';
                    entry.id = typingId;
                    DOM.log.appendChild(entry);
                    DOM.log.scrollTop = DOM.log.scrollHeight;
                }
            }
        });

        state.socket.on('typing_stop', (data) => {
            const typingEntry = document.getElementById(`typing-${data.username}`);
            if (typingEntry) typingEntry.remove();
        });

        state.socket.on('error', (data) => {
            addMessageToLog(`Server error: ${data.message}`, 'error');
        });
    }

    // --- Start the application ---
    initializeSocket();
});