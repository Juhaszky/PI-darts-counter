import { useEffect, useState } from "react";
import { useGameStore } from "../store/gameStore";
import { View, Text, StyleSheet, FlatList } from "react-native";
import { useGame } from "../hooks/useGame";




export default function PlayerModal({onClose, onConfirm, onAddInline}) {
    const { gameState } = useGameStore();
    const { fetchPlayers } = useGame();

    useEffect(() => {
        fetchPlayers();
    }, [gameState?.players]);
    return (
        <View style={styles.container}>
            <FlatList
                data={gameState?.players}
                keyExtractor={(item) => item.id.toString()}
                renderItem={({ item }) => (
                    <View style={styles.playerRow}>
                        <Text style={styles.name}>{item.name}</Text>
                    </View>
                )}
                ListEmptyComponent={
                    <Text style={styles.emptyText}>No players found.</Text>
                }
            />
        </View>
    );
}
const styles = StyleSheet.create({
    container: {
        padding: 10,
        margin: 5,
        backgroundColor: '#f0f0f0',
    },
    playerRow: {
        paddingVertical: 12,
        paddingHorizontal: 10,
        borderBottomWidth: 1,
        borderBottomColor: "#ddd",
    },
    activeContainer: {
        backgroundColor: '#ccc',
    },
    name: {
        fontSize: 18,
        fontWeight: 'bold',
    },
    emptyText: {
        fontSize: 16,
        color: "#666",
        textAlign: "center",
        marginTop: 20,
    },
    score: {
        fontSize: 16,
        color: '#333',
    },
    progressBar: {
        height: 10,
        backgroundColor: '#ddd',
        borderRadius: 5,
        marginTop: 5,
    },
    progressFill: {
        height: '100%',
        backgroundColor: '#4CAF50',
        borderRadius: 5,
    },
    throwIndicator: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 5,
    },
    throwDot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        backgroundColor: '#ccc',
    },
    throwDotActive: {
        backgroundColor: '#4CAF50',
    },
});